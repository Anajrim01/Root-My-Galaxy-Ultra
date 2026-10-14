#!/system/bin/sh
# Restart Samsung's already-running composers while the Android framework is stopped.
# Uses shell builtins plus Android getprop/setprop/sleep; no awk or BusyBox dependency.
case "$(getprop ro.product.manufacturer)" in
    [Ss][Aa][Mm][Ss][Uu][Nn][Gg]) ;;
    *) exit 0 ;;
esac

rmgu_seen=
rmgu_composers=
for rmgu_rc_file in \
    /vendor/etc/init/*.rc /vendor/etc/init/hw/*.rc \
    /odm/etc/init/*.rc /odm/etc/init/hw/*.rc \
    /system/etc/init/*.rc /system/etc/init/hw/*.rc \
    /system_ext/etc/init/*.rc /product/etc/init/*.rc /init*.rc; do
    [ -r "$rmgu_rc_file" ] || continue
    while read -r rmgu_keyword rmgu_name rmgu_binary rmgu_args || [ -n "$rmgu_keyword" ]; do
        [ "$rmgu_keyword" = service ] || continue
        case "$rmgu_binary" in
            *hwcomposer*|*graphics*composer*|*display*composer*|*/hwc|*/hwc[._@-]*|*/composer|*/composer[._@-]*) ;;
            *) continue ;;
        esac
        case " $rmgu_seen " in
            *" $rmgu_name "*) continue ;;
        esac
        rmgu_seen="$rmgu_seen $rmgu_name"
        [ "$(getprop "init.svc.$rmgu_name")" = running ] || continue
        rmgu_composers="$rmgu_composers $rmgu_name"
    done < "$rmgu_rc_file"
done

if [ -z "$rmgu_composers" ]; then
    printf '%s\n' 'RMGU: no running Samsung hardware composer was discovered' >&2
    exit 1
fi

# Remember the complete active set before stopping anything. Coupled services may
# stop together; they must still all receive a start request.
rmgu_restore_needed=1
rmgu_restore_composers() {
    [ "$rmgu_restore_needed" = 1 ] || return 0
    for rmgu_restore_service in $rmgu_composers; do
        setprop ctl.start "$rmgu_restore_service" || :
    done
}
trap rmgu_restore_composers 0
trap 'exit 1' 1 2 15

rmgu_result=0
for rmgu_service in $rmgu_composers; do
    if ! setprop ctl.stop "$rmgu_service"; then
        printf 'RMGU: failed to stop %s\n' "$rmgu_service" >&2
        rmgu_result=1
    fi
done

# Each phase has a shared five-second polling budget, regardless of service count.
rmgu_ticks=0
for rmgu_service in $rmgu_composers; do
    rmgu_state="$(getprop "init.svc.$rmgu_service")"
    while [ "$rmgu_state" != stopped ] && [ "$rmgu_ticks" -lt 50 ]; do
        sleep 0.1
        rmgu_ticks=$((rmgu_ticks + 1))
        rmgu_state="$(getprop "init.svc.$rmgu_service")"
    done
    if [ "$rmgu_state" != stopped ]; then
        printf 'RMGU: stop timeout for %s (%s)\n' "$rmgu_service" "$rmgu_state" >&2
        rmgu_result=1
    fi
done

for rmgu_service in $rmgu_composers; do
    if ! setprop ctl.start "$rmgu_service"; then
        printf 'RMGU: failed to start %s\n' "$rmgu_service" >&2
        rmgu_result=1
    fi
done

rmgu_ticks=0
rmgu_all_running=1
for rmgu_service in $rmgu_composers; do
    rmgu_state="$(getprop "init.svc.$rmgu_service")"
    while [ "$rmgu_state" != running ] && [ "$rmgu_ticks" -lt 50 ]; do
        sleep 0.1
        rmgu_ticks=$((rmgu_ticks + 1))
        rmgu_state="$(getprop "init.svc.$rmgu_service")"
    done
    if [ "$rmgu_state" != running ]; then
        printf 'RMGU: start timeout for %s (%s)\n' "$rmgu_service" "$rmgu_state" >&2
        rmgu_result=1
        rmgu_all_running=0
    fi
done

if [ "$rmgu_all_running" = 1 ]; then
    rmgu_restore_needed=0
fi
exit "$rmgu_result"
