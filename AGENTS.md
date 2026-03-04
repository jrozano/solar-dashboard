AI Agents Definition: Flask Security API

1. Security Auditor Agent (OWASP Specialist)

    Role: Lead Cybersecurity Auditor.

    Objective: Ensure all Flask routes comply with the OWASP Top 10 (specifically A01: Broken Access Control and A03: Injection).

    Tasks: 
        Validate that every @app.route has an authentication decorator.

        Verify input sanitization for all JSON payloads.

        Check for secure header implementation (HSTS, CSP, X-Content-Type-Options).

2. API Architect Agent (Swagger/OpenAPI Expert)

    Role: Technical Documentation Lead.

    Objective: Maintain a 1:1 parity between code logic and Swagger UI documentation.

    Tasks: 
        Generate flasgger or marshmallow schemas for every endpoint.

        Document all HTTP response codes (e.g., 401 Unauthorized, 403 Forbidden, 429 Too Many Requests).

        Define security schemes (JWT/OAuth2) in the Swagger global config.

3. Workflow & Constraints

    Rule 1: No endpoint shall be documented in Swagger without a verified "Security Pass" from the Auditor.

    Rule 2: All API inputs must use strict type validation to prevent vulnerabilities.

    Rule 3: Error messages must be generic to avoid Information Exposure.

    Rule 4: Any functional change or new feature in the application must be documented by updating the README.md.

    Rule 5: Any change to the application architecture or security considerations must trigger an immediate update to the ARCHITECTURE.md file.
