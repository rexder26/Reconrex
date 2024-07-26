#!/bin/python3

import os
import subprocess
import sys

def run_command(command, verbose=False):
    if verbose:
        print(f"Running command: {command}")
    result = subprocess.run(command, shell=True, check=False)
    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}")

def main(url, verbose=False):
    
    subdomains_file = 'subdomains.txt'
    new_subdomains_file = 'tmp/new_subdomains.txt'
    working_domains_file = 'working.domains'
    assets_file = 'tmp/assets.domains'
    os.system('mkdir tmp')
    
    
    for file in [subdomains_file, new_subdomains_file, working_domains_file, assets_file]:
        if not os.path.isfile(file):
            with open(file, 'w') as f:
                pass

    
    print(f"Starting subdomain enumeration for {url}...")
    print("============================")
    subfinder_command = f"subfinder -d {url} -o {subdomains_file}"
    run_command(subfinder_command, verbose)

    
    with open(subdomains_file, 'r') as f:
        subdomains = set(f.read().splitlines())
    print(f"Found {len(subdomains)} subdomains with subfinder.")

    
    user_input = input("Do you want to continue with more subdomain enumeration (Y) or go to asset discovery (N)? ").strip().lower()
    
    if user_input == 'y':
        
        print("Running findomain...")
        print("============================")
        findomain_command = f"findomain -t {url} -u {new_subdomains_file}"
        run_command(findomain_command, verbose)

        print("Running assetfinder...")
        print("============================")
        assetfinder_command = f"assetfinder --subs-only {url} | tee -a {new_subdomains_file}"
        run_command(assetfinder_command, verbose)

        
        with open(new_subdomains_file, 'r') as f:
            new_subdomains = set(f.read().splitlines())

        
        new_unique_subdomains = new_subdomains - subdomains

        
        subdomains.update(new_unique_subdomains)

        
        subdomains = set(subdomains)

        with open(subdomains_file, 'w') as f:
            f.write("\n".join(sorted(subdomains)))
        
        print(f"Total subdomains after additional enumeration: {len(subdomains)}")
    
    
    print("Starting asset discovery process...")
    
    
    print("Running httprobe...")
    print("============================")
    httpx_command = f"cat {subdomains_file} | httprobe | tee {working_domains_file}"
    run_command(httpx_command, verbose)

    with open(working_domains_file, 'r') as f:
        working_domains = f.read().splitlines()
    print(f"Found {len(working_domains)} working domains.")

    
    print("Running gau...")
    print("============================")
    gau_output_file = 'tmp/gau_output.txt'
    gau_command = f"cat {subdomains_file} | gau | tee {gau_output_file}"
    run_command(gau_command, verbose)

    print("Running waybackurls...")
    print("============================")
    waybackurls_output_file = 'tmp/waybackurls_output.txt'
    waybackurls_command = f"cat {subdomains_file} | waybackurls |tee {waybackurls_output_file}"
    run_command(waybackurls_command, verbose)

    print("Running katana...")
    print("============================")
    katana_output_file = 'tmp/katana_output.txt'
    katana_command = f"katana -list {working_domains_file} -o {katana_output_file}"
    run_command(katana_command, verbose)

    print("Running hakrawler...")
    print("============================")
    hakrawler_output_file = 'tmp/hakrawler_output.txt'
    hakrawler_command = f"cat {working_domains_file} | hakrawler |tee {hakrawler_output_file}"
    run_command(hakrawler_command, verbose)

    
    print("Processing final results...")
    print("============================")
    
    with open(gau_output_file, 'r') as f:
        assets = set(f.read().splitlines())
    with open(waybackurls_output_file, 'r') as f:
        assets.update(f.read().splitlines())
    with open(katana_output_file, 'r') as f:
        assets.update(f.read().splitlines())
    with open(hakrawler_output_file, 'r') as f:
        assets.update(f.read().splitlines())

    
    final_assets_file = 'final_assets.txt'
    with open(final_assets_file, 'w') as f:
        f.write("\n".join(sorted(assets)))
    
    print(f"Final assets saved to {final_assets_file}.")
    
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 Reconrex.py <url>")
        sys.exit(1)
    verbose = '-v' in sys.argv
    url = sys.argv[1] if not verbose else sys.argv[2]
    main(url, verbose=verbose)
