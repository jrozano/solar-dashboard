"""Security Headers Tests - Talisman headers validation."""


class TestSecurityHeaders:
    """Talisman must inject standard security headers."""

    def test_x_frame_options_deny(self, client):
        resp = client.get('/api/me')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_x_content_type_options_nosniff(self, client):
        resp = client.get('/api/me')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_referrer_policy(self, client):
        resp = client.get('/api/me')
        assert 'strict-origin' in resp.headers.get('Referrer-Policy', '')

    def test_csp_header_present(self, client):
        """CSP header must be present on API responses."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert csp, 'Content-Security-Policy header is missing'

    def test_csp_frame_ancestors_none(self, client):
        """CSP must include frame-ancestors 'none' to prevent clickjacking."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        assert "frame-ancestors 'none'" in csp

    def test_csp_script_src_no_unsafe_inline(self, client):
        """CSP script-src must NOT contain 'unsafe-inline' on non-Swagger paths."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        script_src = [p for p in csp.split(';') if 'script-src' in p]
        assert script_src, 'script-src directive is missing from CSP'
        assert 'unsafe-inline' not in script_src[0]

    def test_csp_style_src_no_unsafe_inline(self, client):
        """CSP style-src must NOT contain 'unsafe-inline' on non-Swagger paths (SPA)."""
        resp = client.get('/api/me')
        csp = resp.headers.get('Content-Security-Policy', '')
        style_src = [p for p in csp.split(';') if 'style-src' in p]
        assert style_src, 'style-src directive is missing from CSP'
        assert 'unsafe-inline' not in style_src[0], \
            "style-src must not contain 'unsafe-inline' - use external CSS instead"

    def test_session_cookie_flags(self, app):
        """Flask session cookie must have Secure, HttpOnly and SameSite flags."""
        assert app.config['SESSION_COOKIE_SECURE'] is True
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'

    def test_css_file_served(self, client):
        """External CSS file must be served from /style.css."""
        resp = client.get('/style.css')
        assert resp.status_code == 200
        assert 'text/css' in resp.headers.get('Content-Type', '')
        assert 'body' in resp.get_data(as_text=True)

    def test_index_html_no_inline_styles(self, client):
        """index.html must not contain inline style attributes (CSP compliance)."""
        resp = client.get('/')
        html = resp.get_data(as_text=True)
        # Should not have style="..." attributes
        assert 'style="display:none"' not in html, \
            "index.html contains inline display:none - use CSS classes instead"
        assert 'style="font-size:' not in html, \
            "index.html contains inline style attributes - use CSS classes instead"
        # Should link external CSS
        assert '<link rel="stylesheet" href="/style.css"' in html
