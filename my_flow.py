# my_flow.py
import httpx
from prefect import flow, task, get_run_logger
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(cache_key_fn=task_input_hash,cache_expiration=timedelta(days=1))
def get_url(url: str, params: dict = None):
    api_response = httpx.get(url)
    api_response.raise_for_status()
    return api_response.json()

@flow
def get_open_issues(repo_name: str, open_issues_count: int, per_page: int = 100):
    issues = []
    pages = range(1, -(open_issues_count // -per_page) +1)
    for page in pages:
        issues.append(
            # submit method changes the execution from sequential to concurrent
            get_url.submit(
                f"https://api.github.com/repos/{repo_name}/issues",
                params={"page": page, "per_page": per_page, "state": "open"},
            )
        )
    #result method : unpack a list of return values 
    return [i for p in issues for i in p.result()]

@flow(retries=3, retry_delay_seconds=5)
def get_repo_info(repo_owner:str, repo_name: str):
    """ Get repo info -- will retry twice after failing """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    # api_response = httpx.get(url)
    # api_response.raise_for_status()
    # repo_info = api_response.json()
    repo_info = get_url(url)
    return repo_info

@task
def get_contributors(repo_info: dict):
    contributors_url = repo_info["contributors_url"]
    response = httpx.get(contributors_url)
    response.raise_for_status()
    contributors = response.json()
    return contributors

@flow(name="Repo Info",log_prints=True)
def repo_info(repo_owner: str = "langchain-ai", repo_name: str = "langchain"):
    logger = get_run_logger()
    #call `get_repo_info` task
    repo_info = get_repo_info(repo_owner, repo_name)
    issues = get_open_issues(repo_name,repo_info["open_issues_count"])
    issues_per_user = len(issues) / len(set([i["user"]["id"]] for i in issues))

    # logs
    logger.info(f"Repository statistics for {repo_owner}/{repo_name}")
    logger.info(f"Stars :{repo_info['stargazers_count']}")

    # call `get_contributors` task passing upstream results
    contributors = get_contributors(repo_info)
    logger.info(f"Number of Contributors ; {len(contributors)}")

    logger.info(f"Forks : {repo_info['forks_count']}")

    logger.info(f"average open issues per user : {issues_per_user:.2f}")

if __name__ == '__main__':
    # call a flow function for a local flow run
    repo_info()
