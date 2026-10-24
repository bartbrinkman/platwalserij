"""Small test window for the platwalserij sound: trigger button, timeline, toggles.

Space = trigger, R = switch roll recording, W = water on/off, Esc/Q = quit.
"""
import time

import platwals as p  # before pygame: hides its banner
import pygame

W, H = 560, 300
BG, FG, DIM = (30, 32, 36), (230, 230, 230), (120, 124, 130)
BUTTON, BUTTON_BUSY = (200, 90, 40), (90, 60, 50)
PHASES = [  # (label, start, end, colour); roll end filled in from the clip length
    ("slow", p.SLOW_AT, p.FAST_AT, (70, 130, 180)),
    ("fast", p.FAST_AT, p.FAST_END, (90, 170, 220)),
    ("fade", p.FAST_END, p.ROLL_AT, (80, 90, 110)),
    ("roll", p.ROLL_AT, None, (220, 120, 50)),
]
ROLL_NAMES = {"roll": "event 2", "roll_alt": "event 1"}


class Toggle:
    def __init__(self, rect, label):
        self.rect, self.label = pygame.Rect(rect), label

    def draw(self, screen, font, value, on):
        pygame.draw.rect(screen, (70, 110, 80) if on else (60, 62, 68), self.rect, border_radius=8)
        screen.blit(font.render(f"{self.label}: {value}", True, FG), self.rect.move(12, 10))


def main():
    roll_clip = "roll"
    mill = p.Mill(roll_clip, water=False)
    pygame.init()
    pygame.display.set_caption("Platwalserij")
    screen = pygame.display.set_mode((W, H))
    font, big, small = pygame.font.SysFont(None, 26), pygame.font.SysFont(None, 44), pygame.font.SysFont(None, 20)
    trigger = pygame.Rect(20, 20, W - 40, 80)
    roll_toggle = Toggle((20, 230, 255, 44), "Roll (R)")
    water_toggle = Toggle((285, 230, 255, 44), "Water (W)")
    bar = pygame.Rect(20, 140, W - 40, 26)
    clock = pygame.time.Clock()

    def switch_roll():
        nonlocal roll_clip
        if mill.busy.locked():
            return  # don't swap the clip under a running pass
        roll_clip = "roll_alt" if roll_clip == "roll" else "roll"
        mill.set_roll(roll_clip)

    running = True
    while running:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                    mill.trigger()
                elif ev.key == pygame.K_r:
                    switch_roll()
                elif ev.key == pygame.K_w:
                    mill.set_water(not mill.water)
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if trigger.collidepoint(ev.pos):
                    mill.trigger()
                elif roll_toggle.rect.collidepoint(ev.pos):
                    switch_roll()
                elif water_toggle.rect.collidepoint(ev.pos):
                    mill.set_water(not mill.water)

        busy = mill.busy.locked()
        t0 = mill.t0
        elapsed = time.monotonic() - t0 if t0 else None
        total = p.ROLL_AT - p.ROLL_LEAD + mill.snd["roll"].get_length()

        screen.fill(BG)
        pygame.draw.rect(screen, BUTTON_BUSY if busy else BUTTON, trigger, border_radius=12)
        label = big.render("running..." if busy else "TRIGGER  (space)", True, FG)
        screen.blit(label, label.get_rect(center=trigger.center))

        for name, start, end, colour in PHASES:
            end = total if end is None else end
            seg = pygame.Rect(bar.x + bar.w * start / total, bar.y, bar.w * (end - start) / total, bar.h)
            pygame.draw.rect(screen, colour if busy else tuple(c // 2 for c in colour), seg)
            if seg.w > 40:
                screen.blit(small.render(name, True, FG), seg.move(4, 6))
            screen.blit(small.render(f"{start:.0f}s", True, DIM), (seg.x, bar.bottom + 4))
        screen.blit(small.render(f"{total:.0f}s", True, DIM), (bar.right - 22, bar.bottom + 4))
        if elapsed is not None:
            x = bar.x + bar.w * min(elapsed, total) / total
            pygame.draw.line(screen, FG, (x, bar.y - 6), (x, bar.bottom + 6), 3)

        status = mill.status + (f"   {elapsed:4.1f}s" if elapsed is not None else "")
        screen.blit(font.render(status, True, FG), (20, 192))

        roll_toggle.draw(screen, font, ROLL_NAMES[roll_clip], True)
        water_toggle.draw(screen, font, "on" if mill.water else "off", mill.water)
        pygame.display.flip()
        clock.tick(30)

    pygame.mixer.fadeout(800)
    pygame.time.wait(800)
    pygame.quit()


if __name__ == "__main__":
    main()
