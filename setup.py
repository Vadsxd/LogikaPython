import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="Logika",
    version="0.0.2",
    author="Vadsxd",
    author_email="vadim.sannikov.2018@mail.ru",
    description="Logika libs Python Realization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Vadsxd/LogikaPython/Logika",
    project_urls={
        "repository": "https://github.com/Vadsxd/LogikaPython",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "Logika"},
    packages=setuptools.find_packages(where="Logika"),
    python_requires=">=3.11"
)
