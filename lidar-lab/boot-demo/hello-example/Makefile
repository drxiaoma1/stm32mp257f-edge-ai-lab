.DEFAULT_GOAL := all
ifeq ($(origin CC),default)
$(error Run bash build.sh from the hello-lab folder to load the official SDK)
endif
CFLAGS += -Wall -Wextra
.PHONY: all clean
all: hello_world
hello_world: hello_world.o
	$(CC) $(LDFLAGS) -o $@ $^ $(LDLIBS)
hello_world.o: hello_world.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
clean:
	rm -f hello_world hello_world.o
