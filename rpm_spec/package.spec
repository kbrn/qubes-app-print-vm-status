%global _enable_debug_package 0
%global debug_package %{nil}
%global __os_install_post /usr/lib/rpm/brp-compress %{nil}

%define version %(cat version)
%if 0%{?qubes_builder}
%define _builddir %(pwd)
%endif
    
Name:		qubes-app-print-vm-status
Version:	%{version}
Release:	1%{?dist}
Summary:	Qubes CLI VM Status Monitor

Group:		System Environment/Daemons
License:	GPLv2
URL:		https://www.qubes-os.org/

BuildRequires:  systemd

%description
A CLI VM status display tool for Qubes.

%prep
# we operate on the current directory, so no need to unpack anything
# symlink is to generate useful debuginfo packages
rm -f %{name}-%{version}
ln -sf . %{name}-%{version}
%setup -T -D

%build

%install
make install DESTDIR=%{buildroot}

%files
%doc README.md
%defattr(-,root,root,-)
%attr(0774,root,qubes) /usr/local/bin/qubes-print-vm-stats

%changelog

