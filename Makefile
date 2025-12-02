PREFIX ?= /usr/local
BINDIR ?= $(PREFIX)/bin

all:
	@echo "Run 'make install' to install jerry."

install:
	@echo "Installing jerry to $(BINDIR)..."
	mkdir -p $(BINDIR)
	install -m 755 jerry.sh $(BINDIR)/jerry
	install -m 755 jerrydiscordpresence.py $(BINDIR)/jerrydiscordpresence.py
	install -m 755 series_downloader.py $(BINDIR)/series_downloader.py
	@echo "Installation complete. You can now run 'jerry'."

uninstall:
	@echo "Uninstalling jerry from $(BINDIR)..."
	rm -f $(BINDIR)/jerry
	rm -f $(BINDIR)/jerrydiscordpresence.py
	rm -f $(BINDIR)/series_downloader.py
	@echo "Uninstallation complete."

.PHONY: all install uninstall
