#!/usr/bin/env python3
"""Exercise the embedded composer script against mocked Android init properties."""
import json
import os
from pathlib import Path
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'samsung-composer-restart.sh'
MOCK = r'''import json, os, sys, time
from pathlib import Path
p = Path(os.environ['RMGU_TEST_STATE'])
s = json.loads(p.read_text())
cmd = Path(sys.argv[0]).name
args = sys.argv[1:]
if cmd == 'getprop':
    if args[0] == 'ro.product.manufacturer':
        print(s.get('manufacturer', 'samsung'))
    else:
        print(s['services'].get(args[0].removeprefix('init.svc.'), ''))
elif cmd == 'setprop':
    action, service = args
    s.setdefault('calls', []).append([action, service])
    fail = s.get('fail', {}).get(action, {}).get(service, 0)
    if fail:
        s['fail'][action][service] = fail - 1
        p.write_text(json.dumps(s))
        sys.exit(1)
    if service not in s.get('ignore', {}).get(action, []):
        s['services'][service] = 'stopped' if action == 'ctl.stop' else 'running'
    if action == 'ctl.stop':
        for other in s.get('coupled_stop', {}).get(service, []):
            s['services'][other] = 'stopped'
    p.write_text(json.dumps(s))
elif cmd == 'sleep':
    s['sleeps'] = s.get('sleeps', 0) + 1
    p.write_text(json.dumps(s))
    if s.get('pause_for_signal'):
        time.sleep(.25)
else:
    raise SystemExit('Unexpected external command: ' + cmd)
'''


class ComposerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rmgu-composer-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name in ('getprop', 'setprop', 'sleep'):
            path = self.bin / name
            path.write_text('#!' + sys.executable + '\n' + MOCK)
            path.chmod(0o755)
        self.state = self.root / 'state.json'
        # The PATH deliberately has no awk, tr, sort, grep or BusyBox.
        self.env = dict(os.environ, PATH=str(self.bin), RMGU_TEST_STATE=str(self.state))
        text = SCRIPT.read_text()
        for prefix in ('/vendor/etc/init', '/odm/etc/init', '/system/etc/init',
                       '/system_ext/etc/init', '/product/etc/init'):
            text = text.replace(prefix, shlex.quote(str(self.root / prefix.lstrip('/'))))
        self.text = text.replace('/init*.rc', shlex.quote(str(self.root)) + '/init*.rc')

    def rc(self, text, name='vendor/etc/init/composer.rc'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_script(self, services, **extra):
        self.state.write_text(json.dumps(dict(services=services, **extra)))
        result = subprocess.run(['/bin/dash', '-c', self.text], env=self.env,
                                capture_output=True, text=True, timeout=10)
        return result, json.loads(self.state.read_text())

    def test_running_composer_cycles_without_extra_utilities(self):
        self.rc('service vendor.hwc /vendor/bin/hw/android.hardware.graphics.composer3-service.qti\n')
        for manufacturer in ('samsung', 'Samsung', 'SAMSUNG'):
            with self.subTest(manufacturer=manufacturer):
                r, s = self.run_script({'vendor.hwc': 'running'}, manufacturer=manufacturer)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(s['calls'], [['ctl.stop', 'vendor.hwc'], ['ctl.start', 'vendor.hwc']])

    def test_non_samsung_is_untouched(self):
        self.rc('service vendor.hwc /vendor/bin/hw/hwcomposer\n')
        r, s = self.run_script({'vendor.hwc': 'running'}, manufacturer='Other Vendor')
        self.assertEqual(r.returncode, 0)
        self.assertEqual(s.get('calls', []), [])

    def test_comments_other_binaries_and_inactive_services_are_untouched(self):
        self.rc('# service fake /vendor/bin/hw/hwcomposer\n'
                'service composer.telemetry /system/bin/logcat\n'
                'service inactive /vendor/bin/hw/hwcomposer\n'
                'service active /vendor/bin/hw/hwcomposer\n')
        r, s = self.run_script({'fake': 'running', 'composer.telemetry': 'running',
                                'inactive': 'stopped', 'active': 'running'})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(s['calls'], [['ctl.stop', 'active'], ['ctl.start', 'active']])

    def test_duplicate_definitions_and_final_line_without_newline(self):
        self.rc('  service vendor.hwc /vendor/bin/hw/display.composer-service --arg')
        self.rc('service vendor.hwc /vendor/bin/hw/display.composer-service\n', 'odm/etc/init/hw/duplicate.rc')
        r, s = self.run_script({'vendor.hwc': 'running'})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(s['calls'], [['ctl.stop', 'vendor.hwc'], ['ctl.start', 'vendor.hwc']])

    def test_coupled_services_are_all_restarted(self):
        self.rc('service primary /vendor/bin/hw/hwcomposer\n'
                'service secondary /vendor/bin/hw/composer-test\n')
        r, s = self.run_script({'primary': 'running', 'secondary': 'running'},
                                coupled_stop={'primary': ['secondary']})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(s['calls'], [['ctl.stop', 'primary'], ['ctl.stop', 'secondary'],
                                      ['ctl.start', 'primary'], ['ctl.start', 'secondary']])
        self.assertEqual(set(s['services'].values()), {'running'})

    def test_stop_failure_still_attempts_start(self):
        self.rc('service vendor.hwc /vendor/bin/hw/hwcomposer\n')
        r, s = self.run_script({'vendor.hwc': 'running'}, fail={'ctl.stop': {'vendor.hwc': 1}})
        self.assertEqual(r.returncode, 1)
        self.assertIn(['ctl.start', 'vendor.hwc'], s['calls'])
        self.assertEqual(s['services']['vendor.hwc'], 'running')
        self.assertLessEqual(s.get('sleeps', 0), 50)

    def test_stop_timeout_uses_one_shared_budget(self):
        self.rc('service a /vendor/bin/hw/hwcomposer\nservice b /vendor/bin/hw/composer\n')
        r, s = self.run_script({'a': 'running', 'b': 'running'}, ignore={'ctl.stop': ['a', 'b']})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(s['sleeps'], 50)
        self.assertIn(['ctl.start', 'a'], s['calls'])
        self.assertIn(['ctl.start', 'b'], s['calls'])

    def test_failed_start_gets_a_cleanup_retry(self):
        self.rc('service vendor.hwc /vendor/bin/hw/hwcomposer\n')
        r, s = self.run_script({'vendor.hwc': 'running'}, fail={'ctl.start': {'vendor.hwc': 1}})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(s['calls'].count(['ctl.start', 'vendor.hwc']), 2)
        self.assertEqual(s['services']['vendor.hwc'], 'running')
        self.assertEqual(s['sleeps'], 50)

    def test_start_timeout_is_bounded(self):
        self.rc('service vendor.hwc /vendor/bin/hw/hwcomposer\n')
        r, s = self.run_script({'vendor.hwc': 'running'}, ignore={'ctl.start': ['vendor.hwc']})
        self.assertEqual(r.returncode, 1)
        self.assertEqual(s['sleeps'], 50)
        self.assertIn('start timeout', r.stderr)

    def test_missing_composer_reports_failure_without_mutations(self):
        self.rc('service unrelated /system/bin/logcat\n')
        r, s = self.run_script({'unrelated': 'running'})
        self.assertEqual(r.returncode, 1)
        self.assertIn('no running Samsung hardware composer', r.stderr)
        self.assertEqual(s.get('calls', []), [])

    def test_interrupted_child_restores_its_composer(self):
        self.rc('service vendor.hwc /vendor/bin/hw/hwcomposer\n')
        self.state.write_text(json.dumps({'services': {'vendor.hwc': 'running'},
            'ignore': {'ctl.stop': ['vendor.hwc']}, 'pause_for_signal': True}))
        with subprocess.Popen(['/bin/dash', '-c', self.text], env=self.env,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as process:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    if json.loads(self.state.read_text()).get('sleeps'):
                        break
                except json.JSONDecodeError:
                    pass
                time.sleep(.01)
            else:
                process.kill()
                self.fail('Owned test child did not reach the controlled polling phase')
            process.send_signal(signal.SIGTERM)  # Only the child launched by this test.
            process.communicate(timeout=5)
        state = json.loads(self.state.read_text())
        self.assertIn(['ctl.start', 'vendor.hwc'], state['calls'])
        self.assertEqual(state['services']['vendor.hwc'], 'running')

    def test_all_backends_embed_the_reviewed_script(self):
        script = SCRIPT.read_text()
        for name in ('kernelsu', 'kernelsu-next', 'resukisu'):
            patch = (HERE / (name + '-compat.patch')).read_text()
            added = '\n'.join(line[1:] for line in patch.splitlines()
                              if line.startswith('+') and not line.startswith('+++'))
            self.assertIn('r#"' + script + '"#', added, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
