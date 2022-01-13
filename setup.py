from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf8") as fh:
    long_description = fh.read()

setup(
    install_requires=["aiohttp"],
    name="ameilisearch",
    version="0.3.1",
    author="SaidBySolo",
    author_email="saidbysolo@gmail.com",
    description="The python async client for MeiliSearch API.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/saidbysolo/ameilisearch",
    packages=find_packages(),
    project_urls={
        "Documentation": "https://docs.meilisearch.com/",
    },
    keywords="search python meilisearch",
    platform="any",
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={
        "ameilisearch": ["py.typed"],
    },
    include_package_data=True,
    python_requires=">=3",
)
