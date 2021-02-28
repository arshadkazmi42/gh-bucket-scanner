import requests
import base64
import json
import sys


KEYWORDS = ['bucket']
MATCHING_PATTERNS = [
    'bucket:', 'bucket=',
    'bucket_name:', 'bucketName:', 'bucket_name=', 'bucketName=', 
    's3_bucket_name:', 's3BucketName:', 's3_bucket_name=', 's3BucketName=',
    'bucket :', 'bucket =',
    'bucket_name :', 'bucketName :', 'bucket_name =', 'bucketName =', 
    's3_bucket_name :', 's3BucketName :', 's3_bucket_name =', 's3BucketName =',
    's3.amazonaws.com', 's3://', 'amazonaws.com', 
    'gs://', 'storage.googleapis.com'
]


GITHUB_SEARCH_API = 'https://api.github.com/search/code?q='
START_PAGE_NUMBER = 1
SEARCH_QUERY = 'user%3A{}+{}+NOT+test+NOT+example+NOT+sample+NOT+mock&type=Code&page='
GH_RESULTS_PER_PAGE = 30
GH_TOKEN = None
DEBUG = False



# HELPER FUNCTIONS

def _print(text):
    # TODO Add debug / verbose flag / accept from arg
    if DEBUG:
        print(text)

def _get_url(user, keyword):
    searchQuery = SEARCH_QUERY.format(user, keyword)
    _print(searchQuery)
    return f'{GITHUB_SEARCH_API}{searchQuery}'

def _get_github_username():
    args = sys.argv

    if len(args) < 2:
        _print('Missing username!')
        exit()

    return args[1]

def _get_gh_token():
    args = sys.argv

    _print(args)
    _print(len(args))

    if len(args) < 3:
        _print('Missing token')
        return

    return args[2]

def _check_rate_limit(response):
    if response.status_code == 403:
        if 'X-RateLimit-Reset' in response.headers:
            reset_time = int(response.headers['X-RateLimit-Reset'])
            current_time = int(time.time())
            sleep_time = reset_time - current_time + 1
            _print(f'\n\nGitHub Search API rate limit reached. Sleeping for {sleep_time} seconds.\n\n')
            time.sleep(sleep_time)
            return True
    
    return False


def _get_url_result(url, token):

    headers = {}    

    if not token and GH_TOKEN:
        token = GH_TOKEN

    if token:
        headers['Authorization'] = f'token {token}'

    _print(headers)

    response = requests.get(url, headers=headers)

    # if rate limit reached
    # Check and wait for x seconds
    if response.status_code == 403:
        if _check_rate_limit(response):
            response = requests.get(url)

    if response.status_code != 200:
        _print(f'Failed with error code {response.status_code}')
        return {}
        
    return response.json()

def _get_total_pages(url, gh_token):

    result = _get_url_result(f'{url}{START_PAGE_NUMBER}', gh_token)

    total_count = 1
    if 'total_count' in result:
        total_count = result['total_count']

    if total_count > GH_RESULTS_PER_PAGE:
        return int(total_count / GH_RESULTS_PER_PAGE) + 1

    # If total results are less than the total results in one page
    # Return 2, since page_numbers starts with 1.
    # So it needs to do 1 iteration
    return 2


def _decode_base_64(text): 
    return base64.b64decode(text).decode("utf-8") 


def _write_to_file(line):
    f = open(f'{_get_github_username()}.txt', 'a')
    f.write(f'{line}\n')  # python will convert \n to os.linesep
    f.close()


def _search_content(url, content):
    _print(content)
    result = _decode_base_64(content)
    _print(str(result))

    matches = []
    for match in MATCHING_PATTERNS:
        if match in result and 'example' not in url and 'test' not in url:
            print(url)
            _write_to_file(url)
            return

def _is_archived(item, gh_token):
    if 'repository' in item and 'url' in item['repository']:
        repo_url = item['repository']['url']

        repo = _get_url_result(repo_url, gh_token)

        if 'archived' in repo:
            _print(f'{repo["name"]} => Archieved => {str(repo["archived"])}')
            return repo['archived']

        _print(f'{repo["name"]} => Archieved => False')
        return False

    return False

def _get_and_search_content(item, gh_token):

    if _is_archived(item, gh_token):
        return

    if 'url' in item:

        result = _get_url_result(item['url'], gh_token)
        html_url = item['html_url']

        if 'content' in result:
            _search_content(html_url, result['content'])


# MAIN CODE

gh_token = _get_gh_token()

user = _get_github_username()

for keyword in KEYWORDS:

    url = _get_url(user, keyword)

    total_urls = 0
    total_pages = _get_total_pages(url, gh_token)

    for page_number in range(START_PAGE_NUMBER, total_pages):
        
        _print(page_number)
        result = _get_url_result(f'{url}{page_number}', gh_token)

        if 'items' in result:
            items = result['items']

            for item in items:

                _get_and_search_content(item, gh_token)


