# pytemplate

A basic text templating library written in Python.

### Example

See [test.py](test.py).

```python
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
```

And run:

```bash
$ python3 test.py

<html>
  <body>
  
  <article>
    <h1>Hello world!</h1>
    <p>
      This is my first post!
    </p>
  </article>
  
  <article>
    <h1>Take two</h1>
    <p>
      This is a second post.
    </p>
  </article>
  
  </body>
</html>

```
