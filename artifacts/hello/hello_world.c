// SPDX-License-Identifier: BSD-2-Clause
#define _POSIX_C_SOURCE 200809L
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <syslog.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>

#define STUDENT_NAME "mingkang ma"
#define STUDENT_ID "523031910621"

int main(void)
{
    char kernel_message[512], user_message[160], boot_id[64];
    struct timespec uptime;
    struct utsname info;
    size_t used = 0;
    ssize_t count;
    int device = open("/dev/hello_kernel", O_RDONLY | O_CLOEXEC);
    FILE *boot;

    if (device < 0) {
        perror("open /dev/hello_kernel (kernel greeting must happen first)");
        return 1;
    }
    while ((count = read(device, kernel_message + used,
                         sizeof(kernel_message) - 1 - used)) > 0) {
        used += (size_t)count;
        if (used == sizeof(kernel_message) - 1)
            break;
    }
    close(device);
    if (count < 0 || used == 0 || used == sizeof(kernel_message) - 1) {
        fprintf(stderr, "Could not read the complete kernel greeting\n");
        return 1;
    }
    kernel_message[used] = '\0';
    if (strncmp(kernel_message, "[kernel] hello, world", 21) != 0) {
        fprintf(stderr, "Unexpected kernel greeting\n");
        return 1;
    }
    if (clock_gettime(CLOCK_BOOTTIME, &uptime) != 0) {
        perror("clock_gettime");
        return 1;
    }

    puts("Kernel message (read from /dev/hello_kernel):");
    fputs(kernel_message, stdout); /* Replay the earlier kernel print for the screen. */
    puts("");
    snprintf(user_message, sizeof(user_message),
        "[user] hello, world (main, boot +%lld.%03lds)",
        (long long)uptime.tv_sec, uptime.tv_nsec / 1000000);

    /* SECOND greeting: printf in this normal user-space process. */
    printf("%s\n", user_message);
    openlog("hello_user", LOG_PID | LOG_NDELAY, LOG_USER);
    syslog(LOG_INFO, "%s | %s | %s", user_message, STUDENT_NAME, STUDENT_ID);
    closelog();
    printf("Name: %s\nStudent ID: %s\n", STUDENT_NAME, STUDENT_ID);
    printf("User process PID: %ld\n", (long)getpid());
    if (uname(&info) == 0)
        printf("Kernel: %s\nArchitecture: %s\n", info.release, info.machine);
    boot = fopen("/proc/sys/kernel/random/boot_id", "r");
    if (boot) {
        if (fgets(boot_id, sizeof(boot_id), boot))
            printf("Boot ID: %s", boot_id);
        fclose(boot);
    }
    puts("Both stages complete. C1 scan follows automatically.");
    return ferror(stdout) ? 1 : 0;
}
