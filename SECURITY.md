# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. Please do not report security vulnerabilities through public GitHub issues.

Instead, please report them by emailing: **security@grabby.dev**

You should receive a response within 48 hours. If the issue is confirmed, we will release a patch as soon as possible depending on complexity.

## Security Considerations

### Environment Variables

This application requires several environment variables to be set for proper operation:

- **Never commit `.env` files with real credentials to version control**
- Use different `.env` files for different environments (development, staging, production)
- Ensure production secrets are managed through secure secret management systems

### Production Deployment

- Always use HTTPS in production
- Implement proper authentication and authorization
- Use secure database connections (SSL/TLS)
- Regular security updates for all dependencies
- Monitor for security vulnerabilities using tools like Snyk or GitHub Security Advisories

### API Security

- JWT tokens are used for authentication
- Rate limiting is implemented to prevent abuse
- Input validation and sanitization
- CORS properly configured for production domains

## Security Features

- **Password Security**: Bcrypt hashing with configurable cost factor
- **JWT Authentication**: Secure token-based authentication
- **Rate Limiting**: Protection against brute force attacks
- **Input Validation**: All user inputs are validated and sanitized
- **Security Headers**: Proper HTTP security headers implemented
- **Environment Isolation**: Clear separation between development, staging, and production

## Dependencies

We regularly update dependencies to patch security vulnerabilities. If you discover a security issue in a dependency, please report it following the process above.