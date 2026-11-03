#include <stdio.h>
#include <sys/utsname.h>

/* Change these three lines, save, and rebuild. */
#define STUDENT_NAME "mingkang ma"
#define STUDENT_ID   "523031910621"
#define MY_MESSAGE   "My first OpenSTLinux application"

int main(void)
{
    struct utsname info;
    char boot_id[64];
    FILE *boot;

    puts("hello world!");
    printf("Name: %s\n", STUDENT_NAME);
    printf("Student ID: %s\n", STUDENT_ID);
    printf("Message: %s\n", MY_MESSAGE);
    puts("");
    if (uname(&info) == 0) {
        printf("Kernel: %s\n", info.release);
        printf("Architecture: %s\n", info.machine);
    }
    boot = fopen("/proc/sys/kernel/random/boot_id", "r");
    if (boot != NULL) {
        if (fgets(boot_id, sizeof(boot_id), boot) != NULL)
            printf("Boot ID: %s", boot_id);
        fclose(boot);
    }
    printf("Built: %s %s\n", __DATE__, __TIME__);
    puts("Program completed successfully.");
    return 0;
}
