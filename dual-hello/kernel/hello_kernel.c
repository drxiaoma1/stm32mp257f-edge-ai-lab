// SPDX-License-Identifier: GPL-2.0-only
#include <linux/fs.h>
#include <linux/init.h>
#include <linux/ktime.h>
#include <linux/miscdevice.h>
#include <linux/module.h>

/* The device lets the existing display show the actual kernel-origin message. */
static char greeting[160];
static size_t greeting_size;

static ssize_t hello_read(struct file *file, char __user *buf,
                          size_t count, loff_t *position)
{
    return simple_read_from_buffer(buf, count, position, greeting, greeting_size);
}

static const struct file_operations hello_fops = {
    .owner = THIS_MODULE,
    .read = hello_read,
    .llseek = no_llseek,
};

static struct miscdevice hello_device = {
    .minor = MISC_DYNAMIC_MINOR,
    .name = "hello_kernel",
    .fops = &hello_fops,
    .mode = 0444,
};

static int __init hello_kernel_init(void)
{
    unsigned long long ms = ktime_get_boottime_ns() / NSEC_PER_MSEC;
    int result;

    greeting_size = scnprintf(greeting, sizeof(greeting),
        "[kernel] hello, world (hello_kernel_init, boot +%llu.%03llus)\n",
        ms / 1000, ms % 1000);
    result = misc_register(&hello_device);
    if (result)
        return result;

    /* FIRST greeting: this module_init callback executes inside the kernel. */
    pr_info("%s", greeting);
    return 0;
}

static void __exit hello_kernel_exit(void)
{
    misc_deregister(&hello_device);
    pr_info("hello_kernel: unloaded\n");
}

module_init(hello_kernel_init);
module_exit(hello_kernel_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("mingkang ma");
MODULE_DESCRIPTION("Kernel-space boot greeting with a read-only display device");
MODULE_VERSION("1.0");
