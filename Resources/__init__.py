import os
import sys
from xml.etree import ElementTree as ETree

import pygame

from utils import resource_path
from vectors import Vector, vec_like, DIR_ENUMS

__all__ = ["Animation", "predator_anim_dict", "prey_anim_dict", "icons_dict", "app_logo", "title"]

resource_root = resource_path("Resources\\")

if __name__ == '__main__':
    resource_root = resource_path("\\")


def load_atlas(img_path, atlas_path):
    surface = pygame.image.load(img_path)
    with open(atlas_path) as f:
        spec = ETree.parse(f)
        root = spec.getroot()

        sequence_dict = {}
        for sequence in root.iter('sequence'):
            tmp = []
            sequence_dict[sequence.attrib['name']] = tmp
            w = int(sequence.attrib['width'])
            h = int(sequence.attrib['height'])
            for frame in sequence.iter('frame'):
                rect = pygame.Rect(int(frame.attrib["x"]), int(frame.attrib["y"]), w, h)
                tmp.append(surface.subsurface(rect))
    return surface, sequence_dict


class Animation(pygame.sprite.Sprite):

    def __init__(self, atlas_imgs: list[pygame.Surface], region: vec_like = None):
        """A basic animation container class, supports frame random access."""
        super().__init__()
        self._cur_frame = 0
        self._atlas_imgs = atlas_imgs
        self.rect = self._atlas_imgs[0].get_rect()
        self.image = atlas_imgs[0]
        if region is None:
            self._region = Vector(self.rect.width / 2, self.rect.height / 2)
        else:
            self._region = region

    def step(self, num: int = 1):
        """change the current frame by num"""
        self._cur_frame = (self._cur_frame + num) % len(self._atlas_imgs)
        self.image = self._atlas_imgs[self._cur_frame]

    def get_frame_id(self):
        return self._cur_frame

    def set_frame_id(self, frame_id):
        self._cur_frame = frame_id

    def set_position(self, pos: vec_like):
        delta = pos - self._region
        self.move(delta)

    def get_position(self):
        return self._region

    def move(self, vector: vec_like):
        self.rect.move_ip(vector[0], vector[1])
        self._region += vector

    def draw(self, surface: pygame.Surface, size=None):
        if size is not None:
            t_surf = pygame.transform.smoothscale(self.image, size)
            t_rect = t_surf.get_rect()
            t_rect.center = self._region
            surface.blit(t_surf, t_rect)
        else:
            surface.blit(self.image, self.rect)


# load the player animation dictionary
surf, seq_dict = load_atlas(resource_root + "Images\\players\\atlas.png", resource_root + "Images\\players\\atlas.xml")
seq_dict["predator_left"] = [pygame.transform.flip(surf, True, False) for surf in seq_dict["predator_right"]]
seq_dict["prey_left"] = [pygame.transform.flip(surf, True, False) for surf in seq_dict["prey_right"]]
_pred_anim_ls = [
    Animation(seq_dict["predator_left"]),
    Animation(seq_dict["predator_right"]),
    Animation(seq_dict["predator_up"]),
    Animation(seq_dict["predator_down"]),
]
_prey_anim_ls = [
    Animation(seq_dict["prey_left"]),
    Animation(seq_dict["prey_right"]),
    Animation(seq_dict["prey_up"]),
    Animation(seq_dict["prey_down"]),
]
predator_anim_dict = {k: v for k, v in zip(DIR_ENUMS.values(), _pred_anim_ls)}
prey_anim_dict = {k: v for k, v in zip(DIR_ENUMS.values(), _prey_anim_ls)}

# load the icons
icon_root = resource_root + "Images\\icons\\"
icon_paths = list(os.walk(icon_root))[0][2]
icons_dict = {}
for p in icon_paths:
    icons_dict[p[1:-4]] = pygame.image.load(icon_root + p)

# load the app logo and welcome screen title
app_logo = pygame.image.load(resource_root + "Images\\icons\\_game_icon.png")
title = pygame.image.load(resource_root + "Images\\icons\\title.png")

if __name__ == '__main__':
    # A simple test for resource loading module

    pygame.init()
    screen = pygame.display.set_mode((500, 500))
    screen.blit(surf, (0, 0))
    clock = pygame.time.Clock()

    predator = predator_anim_dict[1]
    prey = prey_anim_dict[2]
    n1, n2 = 0, 1

    loopvar = 0
    loopvar2 = 0
    icon_count = len(list(icons_dict.values()))
    while True:
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        screen.fill("gray")

        predator.step()
        prey.step()
        predator.draw(screen, size=(64, 64))
        prey.draw(screen)
        if predator.get_frame_id() == 0:
            n1 = (n1 + 1) % 4
            n2 = (n2 + 1) % 4
            predator = predator_anim_dict[n1 + 1]
            prey = prey_anim_dict[n2 + 1]
            predator.set_position((200, 250))
            prey.set_position((300, 250))

        loopvar = (loopvar + 1) % 60
        screen.blit(pygame.transform.smoothscale(list(icons_dict.values())[loopvar2], (128, 128)), (0, 0))
        if loopvar == 0:
            loopvar2 = (loopvar2 + 1) % icon_count

        pygame.display.flip()
