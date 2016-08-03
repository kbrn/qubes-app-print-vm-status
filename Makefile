install:
	install -d $(DESTDIR)/usr/local/bin/
	install print_vm_stats.py $(DESTDIR)/usr/local/bin/qubes-print-vm-stats
