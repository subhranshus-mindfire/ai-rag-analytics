# Acme Corporation - Information Security & Compliance Standards

## 1. Password & Access Control
- All workforce members must use passwords of at least 14 characters containing uppercase, lowercase, numbers, and symbols.
- Multi-Factor Authentication (MFA) using hardware security keys or authenticator applications is mandatory for all internal and cloud resources.
- Passwords must be rotated every 90 days.

## 2. Data Encryption Standards
- Data at Rest: All relational PostgreSQL databases, vector volumes, and backup archives must be encrypted using AES-256.
- Data in Transit: TLS 1.3 encryption is strictly enforced for all public API and internal communication protocols. Plaintext HTTP traffic is automatically dropped.

## 3. Remote Work & Device Security
- Company-issued devices must maintain full-disk encryption (FileVault / BitLocker) and active endpoint detection software.
- Connecting to public unencrypted Wi-Fi networks without an active corporate VPN is strictly prohibited.
- Lost or stolen devices must be reported to security@acme.example.com within 1 hour.
