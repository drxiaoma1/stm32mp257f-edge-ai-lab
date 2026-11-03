.DEFAULT_GOAL := all
ifeq ($(origin CC),default)
$(error Load the OpenSTLinux SDK environment before running make)
endif
CFLAGS ?= -O2 -g -Wall -Wextra -Werror
PROG := hello_world
OBJS := hello_world.o
DESTDIR ?= $(CURDIR)/install_artifact
PREFIX ?= /usr/local
.PHONY: all clean install
all: $(PROG)
$(PROG): $(OBJS)
	$(CC) $(LDFLAGS) -o $@ $(OBJS) $(LDLIBS)
%.o: %.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@
install: $(PROG)
	install -d $(DESTDIR)$(PREFIX)/bin
	install -m 0755 $(PROG) $(DESTDIR)$(PREFIX)/bin/$(PROG)
clean:
	rm -f $(PROG) $(OBJS)
