import urllib.request
import os

urls = {
    'admin_dashboard.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2YwMjZkMTViYTBkZTQzZjY5ZjdmNjI1ZDg4NWRhZjg2EgsSBxCHjb7F3A0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNzA4NDYyNzM1MTg5OTAwMzI0Ng&filename=&opi=89354086',
    'check.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sX2ExNWVmMjVkMjQwYzQ1Njk5M2FhM2NlNTVkZjJlNmFlEgsSBxCHjb7F3A0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNzA4NDYyNzM1MTg5OTAwMzI0Ng&filename=&opi=89354086',
    'home.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzcwMWVlMDkzZWZhMDQ2M2NhMDY2MjMxMGY5YmZmMjk5EgsSBxCHjb7F3A0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNzA4NDYyNzM1MTg5OTAwMzI0Ng&filename=&opi=89354086',
    'result.html': 'https://contribution.usercontent.google.com/download?c=CgthaWRhX2NvZGVmeBJ8Eh1hcHBfY29tcGFuaW9uX2dlbmVyYXRlZF9maWxlcxpbCiVodG1sXzMzYWQ2NjlkYWVkYTQ1ZjM5N2U4OWZjYTgwYjFkZDYyEgsSBxCHjb7F3A0YAZIBJAoKcHJvamVjdF9pZBIWQhQxNzA4NDYyNzM1MTg5OTAwMzI0Ng&filename=&opi=89354086'
}

os.makedirs('templates', exist_ok=True)
for filename, url in urls.items():
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(os.path.join('templates', filename), 'wb') as out_file:
            data = response.read()
            out_file.write(data)
        print(f"Downloaded {filename}")
    except Exception as e:
        print(f"Failed to download {filename}: {e}")
