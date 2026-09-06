import unittest

from inbox_archaeology.classifier import (
    extract_domain,
    extract_service_name,
    guess_name_from_domain,
    is_signup_subject,
    registrable_domain,
    strip_transactional_subdomain,
)


class SignupSubjectPositiveTests(unittest.TestCase):
    def test_welcome_to(self):
        self.assertTrue(is_signup_subject("Welcome to Spotify!"))

    def test_verify_your_email(self):
        self.assertTrue(is_signup_subject("Please verify your email address"))

    def test_confirm_your_account(self):
        self.assertTrue(is_signup_subject("Confirm your account to get started"))

    def test_activate_your_account(self):
        self.assertTrue(is_signup_subject("Activate your account now"))

    def test_account_has_been_created(self):
        self.assertTrue(is_signup_subject("Your account has been created"))

    def test_complete_your_signup(self):
        self.assertTrue(is_signup_subject("Complete your sign-up to Notion"))

    def test_thanks_for_joining(self):
        self.assertTrue(is_signup_subject("Thanks for joining Duolingo!"))

    def test_case_insensitive(self):
        self.assertTrue(is_signup_subject("WELCOME TO YOUR NEW ACCOUNT"))


class SignupSubjectFalsePositiveTests(unittest.TestCase):
    """The honest part: realistic emails that use similar words but are NOT
    a new-account signal. Each of these documents a real, common email type
    that a naive keyword match would misclassify.
    """

    def test_password_reset_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Reset your password"))

    def test_password_expiring_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Your password is expiring soon"))

    def test_new_login_alert_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("New sign-in to your account from an unrecognized device"))

    def test_suspicious_activity_alert_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Suspicious activity detected on your account"))

    def test_two_factor_code_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Your verification code is 483920"))

    def test_one_time_password_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Your one-time password"))

    def test_email_changed_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Your email address has been changed"))

    def test_order_confirmation_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Order confirmation #48213"))

    def test_receipt_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Your receipt from Uber"))

    def test_unsubscribe_confirmation_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("You have been unsubscribed"))

    def test_combined_welcome_and_password_reset_favors_the_exclusion(self):
        # A real, if slightly unusual, subject line: exclusion patterns win
        # over signup patterns when both are present, since the more
        # specific / higher-stakes signal (password reset) should not be
        # buried by a coincidental "welcome back" framing.
        self.assertFalse(is_signup_subject("Welcome back -- reset your password to continue"))

    def test_an_ordinary_personal_email_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("Re: dinner plans for Friday"))

    def test_a_newsletter_is_not_a_signup(self):
        self.assertFalse(is_signup_subject("This week in tech news"))

    def test_empty_subject(self):
        self.assertFalse(is_signup_subject(""))


class RegistrableDomainTests(unittest.TestCase):
    def test_strips_to_last_two_labels(self):
        self.assertEqual(registrable_domain("notifications.spotify.com"), "spotify.com")
        self.assertEqual(registrable_domain("spotify.com"), "spotify.com")

    def test_lowercases(self):
        self.assertEqual(registrable_domain("SPOTIFY.COM"), "spotify.com")


class StripTransactionalSubdomainTests(unittest.TestCase):
    def test_strips_a_known_prefix(self):
        self.assertEqual(strip_transactional_subdomain("mail.spotify.com"), "spotify.com")
        self.assertEqual(strip_transactional_subdomain("notifications.example.com"), "example.com")

    def test_leaves_an_ordinary_domain_unchanged(self):
        self.assertEqual(strip_transactional_subdomain("spotify.com"), "spotify.com")

    def test_only_strips_one_level(self):
        # Documented limitation, not a bug: chained transactional
        # subdomains are rare enough that guessing further risks eating a
        # real second-level label from an ordinary domain.
        self.assertEqual(
            strip_transactional_subdomain("mail.notifications.example.com"),
            "notifications.example.com",
        )


class GuessNameFromDomainTests(unittest.TestCase):
    def test_simple_domain(self):
        self.assertEqual(guess_name_from_domain("spotify.com"), "Spotify")

    def test_strips_transactional_subdomain_first(self):
        self.assertEqual(guess_name_from_domain("notifications.spotify.com"), "Spotify")

    def test_capitalizes(self):
        self.assertEqual(guess_name_from_domain("EXAMPLE.COM"), "Example")


class ExtractServiceNameTests(unittest.TestCase):
    def test_prefers_a_real_display_name(self):
        self.assertEqual(extract_service_name("Spotify <no-reply@spotify.com>"), "Spotify")

    def test_quoted_display_name(self):
        self.assertEqual(extract_service_name('"Notion" <team@mail.notion.so>'), "Notion")

    def test_falls_back_to_domain_guess_when_display_name_is_generic(self):
        self.assertEqual(extract_service_name("noreply <no-reply@spotify.com>"), "Spotify")

    def test_falls_back_to_domain_guess_when_no_display_name_at_all(self):
        self.assertEqual(extract_service_name("no-reply@spotify.com"), "Spotify")

    def test_no_valid_email_at_all(self):
        self.assertEqual(extract_service_name("not a real header"), "(unknown sender)")


class ExtractDomainTests(unittest.TestCase):
    def test_simple_case(self):
        self.assertEqual(extract_domain("Spotify <no-reply@mail.spotify.com>"), "spotify.com")

    def test_no_email_present(self):
        self.assertIsNone(extract_domain("not a real header"))


if __name__ == "__main__":
    unittest.main()
