.DEFAULT_GOAL := all
ifeq ($(origin CC),default)
$(error Load the official OpenSTLinux SDK environment first)
endif
CFLAGS += -Wall -Wextra -Werror
.PHONY: all clean
all: hello_world
hello_world: hello_world.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $< $(LDFLAGS) $(LDLIBS) -o $@
clean:
	rm -f hello_world
