# SeerAD - Semi-automated AD CTF Assistant

SeerAD is a command-line tool designed to assist in Active Directory CTF challenges by providing a structured approach to managing targets, credentials, and AD operations.

## Installation

SeerAD is installed using pipx, which is the recommended way to install Python applications. Follow these steps:

1. Install pipx if you haven't already:
```bash
python3 -m pip install --user pipx
pipx ensurepath --force
```

2. Install SeerAD:
```bash
pipx install git+https://github.com/Shadow21AR/seerAD
```

## Usage

SeerAD can be used in two modes: interactive shell (preferred) and command-line interface.

### Interactive Shell
Launch the interactive shell:
```bash
seerAD
```

The interactive shell provides a command-line interface for managing targets and credentials. Available commands include:
- `target`: Manage target systems
- `creds`: Manage credentials
- `timewrap`: Manage Kerberos time synchronization
- `reset`: Reset the session
- `version`: Show SeerAD version

### Command-Line Interface
Use specific commands directly:
```bash
seerAD target add <IP> <LABEL> -d <Domain> -f <FQDN> -o <OS>
seerAD creds add <USER> -p <PASS> -n <NTLM> -a <AES128> -A <AES256> -t @<TGT> -c @<CERT> -N <NOTES>
seerAD version
```

## Features

- Target management with IP, domain, and FQDN tracking
- Credential management for various authentication methods (passwords, NTLM, AES keys, tickets)
- Interactive shell with command completion
- Time synchronization for Kerberos operations
- Workspace management for different CTF challenges

## Requirements

- Python 3.8 or higher
- pipx (recommended for installation)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License