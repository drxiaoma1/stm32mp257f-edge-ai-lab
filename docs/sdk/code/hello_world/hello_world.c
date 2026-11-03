#include <stdio.h>
#include <sys/utsname.h>
#include <unistd.h>

int main(void)
{
    struct utsname info;
    setbuf(stdout, NULL);
    puts("hello world!");
    puts("Student: mingkang ma");
    puts("Student ID: 523031910621");
    puts("User space program: edge-ai midterm");
    if (uname(&info) == 0)
        printf("Running kernel: %s | Architecture: %s\n", info.release, info.machine);
    FILE *fp = fopen("/proc/sys/kernel/random/boot_id", "r");
    if (fp) {
        char boot_id[64];
        if (fgets(boot_id, sizeof(boot_id), fp)) printf("Boot ID: %s", boot_id);
        fclose(fp);
    }
    for (int i = 3; i > 0; --i) { printf("Countdown: %d\n", i); sleep(1); }
    puts("hello world completed successfully");
    return 0;
}
