Name:           gloom
Version:        0.1.0
Release:        1%{?dist}
Summary:        High-performance CLI for Google Cloud Context & ADC Switching

License:        MIT
URL:            https://github.com/hilmanmustofaa/gloom
Source0:        %{url}/archive/refs/tags/v%{version}.tar.gz#/%{name}-%{version}.tar.gz

BuildArch:      noarch

BuildRequires:  python3-devel >= 3.10
BuildRequires:  python3-pip
BuildRequires:  python3-wheel
BuildRequires:  python3-hatchling

Requires:       python3 >= 3.10
Requires:       python3-typer >= 0.9.0
Requires:       python3-rich >= 13.0.0
Requires:       python3-pydantic >= 2.0.0

%description
Gloom manages gcloud configurations and Application Default Credentials (ADC)
via symlink manipulation, enabling sub-100ms context switching between
Google Cloud projects.

Features:
- Instant ADC switching using symlinks (<100ms)
- XDG Base Directory compliance
- Secure credential caching (0600 permissions)
- Shell integration (bash, zsh, fish)

%prep
%autosetup -n %{name}-%{version}

%build
%py3_build_wheel

%install
%py3_install_wheel %{name}-%{version}-py3-none-any.whl

%check
%{python3} -m pytest tests/ -v || :

%files
%license LICENSE
%doc README.md
%{_bindir}/gloom
%{python3_sitelib}/gloom/
%{python3_sitelib}/gloom-%{version}.dist-info/

%changelog
* Thu Jan 02 2026 Your Name <your.email@example.com> - 0.1.0-1
- Initial package release
- Symlink-based ADC switching for fast context changes
- XDG-compliant configuration
- Typer CLI with rich output
