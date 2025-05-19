import unittest
from shorthorn_nlp_scraper import search_members_table, extract_place_parts, extract_member_name, get_t_param

class TestShorthornNlpScraper(unittest.TestCase):

    def test_extract_place_parts(self):
        self.assertEqual(extract_place_parts("search from virginia"), ("virginia", ""))
        self.assertEqual(extract_place_parts("search from jemison city"), ("", "jemison"))
        self.assertEqual(extract_place_parts("search from virginia and jemison city"), ("virginia", "jemison"))

    def test_extract_member_name(self):
        self.assertEqual(extract_member_name("search member name abby mill"), "abby mill")
        self.assertEqual(extract_member_name("search member name"), "")
        self.assertIn("abby", extract_member_name("search member name abby"))

    def test_get_t_param(self):
        self.assertEqual(get_t_param("virginia", "", "", "search from virginia"), "574")
        self.assertEqual(get_t_param("", "", "abby mill", "search member name abby mill"), "901")
        self.assertEqual(get_t_param("", "", "abby", "search member name abby"), "966")
        self.assertEqual(get_t_param("", "jemison", "", "search from jemison city"), "978")
        self.assertEqual(get_t_param("virginia", "jemison", "", "search from virginia and jemison city"), "803")
        self.assertEqual(get_t_param("United States", "", "", "search all states"), "897")

    def test_build_search_url(self):
        url = search_members_table("show me all member from all states")
        self.assertIsNotNone(url)
        self.assertIn("t=897", url)
        self.assertIn("united+states%7c", url.lower())

        url = search_members_table("show me all member from virginia")
        self.assertIsNotNone(url)
        self.assertIn("t=574", url)
        self.assertIn("united+states%7cva", url.lower())

        url = search_members_table("show me all member from jemison city")
        self.assertIsNotNone(url)
        self.assertIn("t=803", url) 
        self.assertIn("jemison", url.lower())


        url = search_members_table("show me all members with the name abby")
        self.assertIsNotNone(url)
        self.assertIn("abby", url.lower())
        self.assertIn("t=574", url) 

        url = search_members_table("show me all member from alabama and jemison city")
        self.assertIsNotNone(url)
        self.assertIn("jemison", url.lower())
        self.assertIn("al", url.lower())
        self.assertIn("t=803", url)



if __name__ == "__main__":
    unittest.main()
