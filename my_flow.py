# my_flow.py
import httpx
from prefect import flow, task, get_run_logger

@task(retries=2)
def get_repo_info(repo_owner:str, repo_name: str):
    """ Get repo info -- will retry twice after failing """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}"
    api_response = httpx.get(url)
    api_response.raise_for_status()
    repo_info = api_response.json()
    return repo_info

@task
def get_contributors(repo_info: dict):
    contributors_url = repo_info["contributors_url"]
    response = httpx.get(contributors_url)
    response.raise_for_status()
    contributors = response.json()
    return contributors

@flow(name="Repo Info",log_prints=True)
def repo_info(repo_owner: str = "PrefectHQ", repo_name: str = "prefect"):
    logger = get_run_logger()
    #call `get_repo_info` task
    repo_info = get_repo_info(repo_owner, repo_name)
    logger.info(f"Repository statistics for {repo_owner}/{repo_name}")
    logger.info(f"Stars :{repo_info['stargazers_count']}")

    # call `get_contributors` task passing upstream results
    contributors = get_contributors(repo_info)
    logger.info(f"Number of Contributors ; {len(contributors)}")

    logger.info(f"Forks : {repo_info['forks_count']}")
if __name__ == '__main__':
    # call a flow function for a local flow run
    repo_info()
