import time
import psutil
import win32gui
import win32process
import win32con

TARGET_PROCESS = [
    "UniKeyNT.exe",
    "PhoneExperienceHost.exe",
    "ChatGPT.exe"
]

def log(msg):
    with open('D:/log.txt','a',encoding='utf-8') as f:
        f.writelines(msg+'\n')

closed_windows = set()
seen_process = set()
no_window_count = {name: 0 for name in TARGET_PROCESS}

start_time = time.perf_counter()
TIMEOUT = 300

def get_pids_by_name(name):
    return [p.info['pid'] for p in psutil.process_iter(['name', 'pid']) if p.info['name'] == name]


def get_windows_by_pid(pid):
    result = []

    def callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return

        _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
        if found_pid == pid:
            result.append(hwnd)

    win32gui.EnumWindows(callback, None)
    return result


while True:
    now = time.perf_counter()

    if now - start_time > TIMEOUT:
        log(f"[EXIT] Timeout sau {TIMEOUT}s")
        break

    for proc_name in TARGET_PROCESS[:]:
        pids = get_pids_by_name(proc_name)

        all_windows = []
        for pid in pids:
            all_windows.extend(get_windows_by_pid(pid))

        if all_windows:
            seen_process.add(proc_name)
            no_window_count[proc_name] = 0
        else:
            no_window_count[proc_name] += 1

        if proc_name not in seen_process:
            continue
  
        if no_window_count[proc_name] >= 5:
            log(f"[REMOVE] {proc_name} sau 3 loop không còn window")
            TARGET_PROCESS.remove(proc_name)
            continue
        new_windows = [hwnd for hwnd in all_windows if hwnd not in closed_windows]

        for hwnd in new_windows:
            try:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                closed_windows.add(hwnd)

                t = now - start_time
                log(f"[CLOSED] {proc_name} | hwnd={hwnd} | t={t:.2f}s")

            except Exception as e:
                log(f"[ERROR] hwnd={hwnd}: {e}")

    if not TARGET_PROCESS:
        log("[DONE] Không còn process cần xử lý")
        break

    time.sleep(1)