from setuptools import setup

setup(name='aiocmd',
      py_modules=['aiocmd'],
      version='0.1',
      author='Dor Green',
      author_email='dorgreen1@gmail.com',
      description='.',
      url='http://github.com/KimiNewt/aiocmd',
      keywords=['asyncio', 'cmd'],
      license='MIT',
      install_requires=[
          'prompt_toolkit>=2.0.9'
      ],
      classifiers=[
          'License :: OSI Approved :: MIT License',

          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python :: 3.6',
          'Programming Language :: Python :: 3.7'
      ])
