# Foodgram
Проект развернут на домене foodfavorite.zapto.org

### Описание:
Проект позволяет просматривать и публиковать рецепты блюд.
Добавление рецептов доступно только авторизованным пользователям.
Просмотр рецептов доступен всем.
Для создания рецепта необходимо указать наименование блюда, теги,
к которым относится рецепт, список ингредиентов, время приготовления,
порядок приготовления и прикрепить картинку.
У зарегистрированных пользователей также есть следующие возможности:
- подписаться на другого пользователя
- добавить рецепт в список избранного
- добавить рецепт в список покупок
- сформировать список покупок в формате txt. В этот список добавятся
 ингредиенты, которые необходимы для приготовления блюд, включенных
 в список покупок с учетом количества.
 - добавление аватара к своему профилю.
 Теги и ингредиенты может добавлять только администратор проекта.

### Как развернуть проект:
* Создать на серервере для проекта папку foodgram
* Скопировать в нее файл docker-compose.production.yml
  Для этого можно создать на сервере файл docker-compose.production.yml
  с помощью команды sudo nano (имя файла) и добавьть в него содержимое из
  локального docker-compose.production.yml.
* Запустить Docker Compose в режиме демона. Находясь в папке foodgram
  выполнить команду
  sudo docker compose -f docker-compose.production.yml up -d 
* Выполнить миграции, соберать статические файлы бэкенда и скопировать их
  в директорию /backend_static/static/ с помощью следующих команд:
  sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
  sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
  sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/

### Как загрузить список ингредиентов:
Скоприровать файл ingredients.json в папку backend
Выполнить деплой проекта (сохранить изменения на GitHub)
На сервере запустить команду: 
sudo docker exec -it foodgram-backend-1 python manage.py load_ingredients ingredients.json

### Как открыть документацию:
Находясь в папке infra, выполните команду docker-compose up. При выполнении этой команды
контейнер frontend, описанный в docker-compose.yml, подготовит файлы, необходимые для
работы фронтенд-приложения, а затем прекратит свою работу.
По адресу http://localhost/api/docs/ — будет доступна спецификация API.

### Примеры запросов к API:
Получить список всех рецептов:
Выводится список всех рецептов, разбитый на страницы.
(Запрос от авторизованного пользователя)

```
GET http://foodfavorite.zapto.org/api/pecipes/
```

Создание рецепта:
(Запрос от авторизованного пользователя)
```
POST http://foodfavorite.zapto.org/api/pecipes/
```
```
{
  "ingredients": [
    {
      "id": 1123,
      "amount": 10
    }
  ],
  "tags": [
    1,
    2
  ],
  "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAgMAAABieywaAAAACVBMVEUAAAD///9fX1/S0ecCAAAACXBIWXMAAA7EAAAOxAGVKw4bAAAACklEQVQImWNoAAAAggCByxOyYQAAAABJRU5ErkJggg==",
  "name": "string",
  "text": "string",
  "cooking_time": 1
}
```

## Технологии
* Python - версия 3.9.13
* Django — основной фреймворк для разработки.
* Django REST Framework — для создания API.
* PostgreSQL — в качестве базы данных.
* Joser — для аутентификации пользователей.

## Авторы
* [Ludmila Usacheva](https://github.com/Lusya4400)
* Команда разработки курса Python-разработчик Яндекс Практикума
