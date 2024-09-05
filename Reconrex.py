#!/bin/python3

import os,sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_command(command, verbose=False):
    if verbose:
        print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")

def process_domain(url, verbose=False):
    subdomains_file = f'tmp/{url}_subdomains.txt'
    new_subdomains_file = f'tmp/{url}_new_subdomains.txt'
    working_domains_file = f'tmp/{url}_working.domains'
    assets_file = f'tmp/{url}_assets.domains'
    os.system('mkdir -p tmp')
    
    for file in [subdomains_file, new_subdomains_file, working_domains_file, assets_file]:
        if not os.path.isfile(file):
            with open(file, 'w') as f:
                pass

    print(f"Starting subdomain enumeration for {url}...")
    print("============================")
    subfinder_command = f"subfinder -silent -recursive -all -nc -d {url} -o {subdomains_file}"
    run_command(subfinder_command, verbose)

    with open(subdomains_file, 'r') as f:
        subdomains = set(f.read().splitlines())
    print(f"Found {len(subdomains)} subdomains with subfinder.")

    user_input = input("Do you want to continue with more subdomain enumeration (Y) or go to asset discovery (N)? ").strip().lower()
    
    if user_input == 'y':
        print("Running findomain...")
        print("============================")
        findomain_command = f"findomain --quiet --no-wildcards -t {url} -u {new_subdomains_file}"
        run_command(findomain_command, verbose)

        print("Running assetfinder...")
        print("============================")
        assetfinder_command = f"assetfinder -subs-only {url} | tee -a {new_subdomains_file}"
        run_command(assetfinder_command, verbose)

        with open(new_subdomains_file, 'r') as f:
            new_subdomains = set(f.read().splitlines())

        new_unique_subdomains = new_subdomains - subdomains
        subdomains.update(new_unique_subdomains)

        with open(subdomains_file, 'w') as f:
            f.write("\n".join(sorted(subdomains)))
        
        print(f"Total subdomains after additional enumeration: {len(subdomains)}")
    
    print("Starting asset discovery process...")
    print("============================")
    
    print("Running httpx...")
    httpx_command = f"cat {subdomains_file} | httpx -sc -title -ip -cname -cdn -cl -vhost -fr -fhr -j -srd allweb | tee tmp/{url}_alive_status"
    run_command(httpx_command, verbose)

    print("Filtering Live Domains...")
    alive_command = (
        f"jq '. | select(.status_code >= 300 or .status_code < 400 )' tmp/{url}_alive_status | grep final_url | "
        f"grep \"{url}\" | cut -d '\"' -f4 | sed 's|/$||'| sort -u | tee tmp/{url}_temp.url && "
        f"jq '. | if .final_url == null then .url else .final_url end' tmp/{url}_alive_status | cut -d '\"' -f2 | "
        f"sort -u | grep \"{url}\" | tee -a tmp/{url}_temp.url && "
        f"jq .cname tmp/{url}_alive_status | grep \"{url}\" | cut -d '\"' -f2 | sort -u | httpx -fc 500,502,503 | tee -a tmp/{url}_temp.url &&"
        f"cat tmp/{url}_temp.url | sort -u | tee {working_domains_file}"
    )
    run_command(alive_command, verbose)

    with open(working_domains_file, 'r') as f:
        working_domains = f.read().splitlines()
    print(f"Found {len(working_domains)} working domains.")
    
    
    def run_gau():
        print("Running gau...")
        gau_output_file = f'tmp/{url}_gau_output.txt'
        gau_command = f"cat {subdomains_file} | gau --subs --threads 5 | tee {gau_output_file}"
        run_command(gau_command, verbose)
    
    def run_waybackurls():
        print("Running waybackurls...")
        waybackurls_output_file = f'tmp/{url}_waybackurls_output.txt'
        waybackurls_command = f"cat {subdomains_file} | waybackurls | tee {waybackurls_output_file}"
        run_command(waybackurls_command, verbose)

    def run_katana():
        print("Running katana...")
        katana_output_file = f'tmp/{url}_katana_output.txt'
        katana_command = f"katana -d 10 -jc -jsl -hl -list {working_domains_file} -o {katana_output_file}"
        run_command(katana_command, verbose)

    def run_hakrawler():
        print("Running hakrawler...")
        hakrawler_output_file = f'tmp/{url}_hakrawler_output.txt'
        hakrawler_command = f"cat {working_domains_file} | hakrawler -d 10 -subs | tee {hakrawler_output_file}"
        run_command(hakrawler_command, verbose)

    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(run_gau),
            executor.submit(run_waybackurls),
            executor.submit(run_katana),
            executor.submit(run_hakrawler),
        ]
        
        
        for future in as_completed(futures):
            future.result()  
    
    print("Processing final results...")
    with open(f'tmp/{url}_gau_output.txt', 'r') as f:
        assets = set(f.read().splitlines())
    with open(f'tmp/{url}_waybackurls_output.txt', 'r') as f:
        assets.update(f.read().splitlines())
    with open(f'tmp/{url}_katana_output.txt', 'r') as f:
        assets.update(f.read().splitlines())
    with open(f'tmp/{url}_hakrawler_output.txt', 'r') as f:
        assets.update(f.read().splitlines())

    final_assets_file = f'final_assets_{url}.txt'
    with open(final_assets_file, 'w') as f:
        f.write("\n".join(sorted(assets)))
    
    print(f"Final assets saved to {final_assets_file}.")

    
    return subdomains, assets

def main(verbose=False):
    domains_file = 'domains.txt'  
    
    if not os.path.isfile(domains_file):
        print(f"Domains file '{domains_file}' not found.")
        return
    
    with open(domains_file, 'r') as f:
        urls = f.read().splitlines()

    all_subdomains = set()
    all_final_assets = set()

    for url in urls:
        subdomains, final_assets = process_domain(url, verbose=verbose)
        all_subdomains.update(subdomains)
        all_final_assets.update(final_assets)

    
    with open('all_subdomains.txt', 'w') as f:
        f.write("\n".join(sorted(all_subdomains)))

    with open('all_final_assets.txt', 'w') as f:
        f.write("\n".join(sorted(all_final_assets)))

    print("All subdomains saved to all_subdomains.txt")
    print("All final assets saved to all_final_assets.txt")

if __name__ == "__main__":
    verbose = '-v' in sys.argv
    main(verbose=verbose)
