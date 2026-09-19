# Endless Maze

![version](https://img.shields.io/badge/version-0.1-blue)

A maze game features real-time randomized maze generating using an original algorithm; single mode & two-player
chasing mode (still developing); a pretty game UI and game data storage. Made by two students from Beijing Institute of Technology.

## How to Play

you can run the game directly by running main.py using the command below, or run the executable .exe file in the
dist/ folder.

```shell
pythonw main.py
```

## Expand The Game

We have always attached importance to the scalability of the game throughout the development process.
We provided APIs including Maze dumping & loading, vector operation, animation effects etc. 
Each base class has a comprehensive document for the developers who want to modify the game or the algorithm.

## What's the limitations

Now the effect class is not optimized, it uses the pygame functions to munk in-place modification, this causes about 2
times more blits. The next step we are going to optimize this class using Pygame.SurfArray and Numpy.

