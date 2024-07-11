# LogikaPython
Перевод библиотек для работы с приборами с C# на Python

# Как сделать дистрибутивы
## Linux
+ ```python3 -m pip install --upgrade build```
+ ```python3 -m build```

## Windows
+ ```python.exe -m pip install --upgrade build```
+ ```python.exe -m build```

# Как загрузить дистрибутивы в PyPI
## Linux
+ ```python3 -m pip install --upgrade twine```
+ ```python3 -m twine upload --repository testpypi dist/*```

## Windows
+ ```py -m pip install --upgrade twine```
+ ```py -m twine upload --repository testpypi dist/*```

# Как установить пакеты
+ ```pip install -i https://test.pypi.org/simple/ Logika==0.0.2```
