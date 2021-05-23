from pytemplate import eval_template

template = '''
<html>
  <body>
  {% for-in(post, posts) %}
  <article>
    <h1>{{ get(post, 'title') }}</h1>
    <p>
      {{ get(post, 'body') }}
    </p>
  </article>
  {% endfor-in %}
  </body>
</html>
'''

env = {
    'posts': [
        {
            'title': 'Hello world!',
            'body': 'This is my first post!',
        },
        {
            'title': 'Take two',
            'body': 'This is a second post.',
        },
    ],
}

print(eval_template(template, env))
