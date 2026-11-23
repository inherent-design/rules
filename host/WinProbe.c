/* Windows 11 probe. Build with cl /W4 host\WinProbe.c or cross-compile
   using zig cc -target x86_64-windows-gnu host/WinProbe.c -o WinProbe.exe. */
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <io.h>
#include <stdint.h>
static void require(BOOL ok, const char *operation) {
    if (!ok) {
        fprintf(stderr, "%s failed (%lu)\n", operation, GetLastError());
        exit(1);
    }
}
static HANDLE open_file(const WCHAR *path, DWORD access) {
    HANDLE file = CreateFileW(path, access, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                              NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    require(file != INVALID_HANDLE_VALUE, "CreateFileW");
    return file;
}
static void write_one(const WCHAR *path, char value) {
    DWORD n;
    HANDLE file = open_file(path, GENERIC_WRITE);
    require(WriteFile(file, &value, 1, &n, NULL) && n == 1, "WriteFile");
    CloseHandle(file);
}
static int read_one(HANDLE file) {
    char value;
    DWORD n;
    require(ReadFile(file, &value, 1, &n, NULL) && n == 1, "ReadFile");
    return value - 'A';
}
static void files(void) {
    WCHAR dir[MAX_PATH], live[MAX_PATH], staged[MAX_PATH];
    DWORD length = GetTempPathW(MAX_PATH, dir);
    require(length > 0 && length < MAX_PATH, "GetTempPathW");
    require(GetTempFileNameW(dir, L"rul", 0, live) != 0, "allocate target");
    require(GetTempFileNameW(dir, L"rul", 0, staged) != 0, "allocate stage");
    write_one(live, 'A');
    write_one(staged, 'B');
    HANDLE before = open_file(live, GENERIC_READ);
    require(ReplaceFileW(live, staged, NULL, 0, NULL, NULL), "ReplaceFileW");
    HANDLE after = open_file(live, GENERIC_READ);
    printf("{\"v\":1,\"surface\":\"file\",\"case\":\"win-held\",\"observed\":{\"opened_before\":true,\"replaced\":true},\"outcome\":{\"decision\":%d}}\n", read_one(before));
    printf("{\"v\":1,\"surface\":\"file\",\"case\":\"win-fresh\",\"observed\":{\"opened_before\":false,\"replaced\":true},\"outcome\":{\"decision\":%d}}\n", read_one(after));
    CloseHandle(before);
    CloseHandle(after);
    require(DeleteFileW(live), "remove owned target");
}
static DWORD WINAPI work(void *gate) {
    return WaitForSingleObject((HANDLE)gate, 5000) == WAIT_OBJECT_0 ? 7 : 1;
}
int main(void) {
    files();
    HANDLE gate = CreateEventW(NULL, TRUE, FALSE, NULL);
    require(gate != NULL, "CreateEventW");
    HANDLE thread = CreateThread(NULL, 0, work, gate, 0, NULL);
    require(thread != NULL, "CreateThread");
    require(WaitForSingleObject(thread, 0) == WAIT_TIMEOUT, "bounded wait");
    DWORD code;
    require(GetExitCodeThread(thread, &code), "GetExitCodeThread");
    printf("{\"v\":1,\"surface\":\"work\",\"case\":\"win-timeout\",\"observed\":{\"requested_stop\":false,\"witnessed_end\":false},\"outcome\":{\"decision\":%d}}\n", code != STILL_ACTIVE);
    require(SetEvent(gate), "SetEvent");
    require(WaitForSingleObject(thread, 5000) == WAIT_OBJECT_0, "join thread");
    require(GetExitCodeThread(thread, &code), "read worker result");
    printf("{\"v\":1,\"surface\":\"work\",\"case\":\"win-retired\",\"observed\":{\"requested_stop\":false,\"witnessed_end\":true},\"outcome\":{\"decision\":%d}}\n", code == 7);
    CloseHandle(thread);
    CloseHandle(gate);
    DWORD ids[] = {STD_INPUT_HANDLE, STD_OUTPUT_HANDLE, STD_ERROR_HANDLE};
    for (unsigned i=0; i<3; i++) {
        DWORD mode;
        HANDLE h = GetStdHandle(ids[i]);
        fprintf(stderr, "fd%u GetFileType=%lu GetConsoleMode=%d crt_isatty=%d\n",
                i, GetFileType(h), !!GetConsoleMode(h, &mode), !!_isatty(i));
    }
    return 0;
}
