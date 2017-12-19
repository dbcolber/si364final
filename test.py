import requests
import json
import unittest
from food2fork import get_or_create_recipes, db, app, mail, get_or_create_searchword
import os

## Test Suite

def getting_recipe_api(food):
    base = 'http://food2fork.com/api/search'
    r = requests.get(base, params={'key':'ea94673565a10487854263cbdb7fc32c', 'q':food})
    r_dic = r.json()
    recipe1 = r_dic['recipes'][0]
    return recipe1

# print(getting_recipe_api('pasta'))

class TestCase(unittest.TestCase):

    def test_api_1(self):
        pasta = getting_recipe_api('pasta')
        self.assertEqual(type(pasta["title"]), type(""), "Testing that the Food2Fork API returns a string for the title of the recipe")

    def test_api_2(self):
        pasta = getting_recipe_api('pasta')
        self.assertEqual(pasta['source_url'], 'http://thepioneerwoman.com/cooking/2011/06/pasta-with-pesto-cream-sauce/', "Testing that the top rated pasta recipe matches this soruce url")

    def test_api_3(self):
        searchword = "pineapple pizza"
        pizza = getting_recipe_api(searchword)
        self.assertEqual(type(pizza), type({}), "Testing that the API returns a dictionary that can later be parsed in my code for when I put the data into my database")

    def test_api_4(self):
        searchword = "pineapple pizza"
        pizza = getting_recipe_api(searchword)
        self.assertEqual(len(pizza), 8, "Testing that the Food2Fork API returns a dictionary with 8 keys")

    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get('DATABASE_URL') or "postgresql://localhost/testdb"
        self.app = app.test_client()
        db.drop_all()
        db.create_all()
 
    # executed after each test
    def tearDown(self):
        pass 

    def test_app_routes(self):
        resp = self.app.get('/', follow_redirects=True)
        self.assertEqual(resp.status_code, 200, "Testing that the status code is 200 when the user goes to the index")

    def test_app_routes_2(self):
        resp = self.app.get('/jdfksla;js', follow_redirects=True)
        self.assertEqual(resp.status_code, 500, "Testing that this nonsense string returns a 505 error")        

    def test_app_routes_3(self):
        resp = self.app.get('/cookbook', follow_redirects=True)
        self.assertEqual(resp.status_code, 200, "Testing that the status code is 200 when the user goes to the /cookbook route")

# testing the addition of a new recipe to the database
    def test_recipes(self):
        pasta = getting_recipe_api('pasta')
        all_keys = []
        counter = 0
        for item in pasta:
            counter += 1
            print(counter, item)
            all_keys.append(item)
        self.assertEqual(len(all_keys), 8, "Testing the number of keys in a recipe request")

if __name__ == '__main__':
    unittest.main()


