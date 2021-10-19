import retro
import time
import numpy
import cv2

buttons = {
    'LEFT':[False, False, False, False, False, False, True, False, False, False, False, False],
    'RIGHT':[False, False, False, False, False, False, False, True, False, False, False, False],
    'DOWN':[False, False, False, False, False, True, False, False, False, False, False, False],
    'B':[True, False, False, False, False, False, False, False, False, False, False, False],
    'Y':[False, True, False, False, False, False, False, False, False, False, False, False],
    'A':[False, False, False, False, False, False, False, False, True, False, False, False],
    'DOWNY':[False, True, False, False, False, True, False, False, False, False, False, False],
    'LEFTY':[False, True, False, False, False, False, True, False, False, False, False, False],
    'RIGHTY':[False, True, False, False, False, False, False, True, False, False, False, False]
}

def get_move(key_array):
    for key, value in buttons.items():
        if numpy.array_equal(value, key_array):
            print(key)
            return key

def draw_image(img, drawn, move):
    drawn = img.copy()
    if move is None:
        return
    if move == 'B':
        drawn = cv2.circle(drawn,(577, 269), 26, (0,0,255), -1)
    if 'Y' in move:
        drawn = cv2.circle(drawn,(514, 215), 26, (0,0,255), -1)
    if 'LEFT' in move:
        start_point = (130, 203)
        end_point = (start_point[0] + 25, start_point[1] + 25)
        drawn = cv2.rectangle(drawn, start_point, end_point, (0,0,255), -1)
    if 'RIGHT' in move:
        start_point = (204, 203)
        end_point = (start_point[0] + 25, start_point[1] + 25)
        drawn = cv2.rectangle(drawn, start_point, end_point, (0,0,255), -1)
    if 'DOWN' in move:
        start_point = (167, 240)
        end_point = (start_point[0] + 25, start_point[1] + 25)
        drawn = cv2.rectangle(drawn, start_point, end_point, (0,0,255), -1)
    cv2.imshow('sample image',drawn)
        
    cv2.waitKey(3)

movie = retro.Movie('best-TimeStep-1255.bk2')
movie.step()

env = retro.make(
    game=movie.get_game(),
    state=None,
    # bk2s can contain any button presses, so allow everything
    use_restricted_actions=retro.Actions.ALL,
    players=movie.players,
)
env.initial_state = movie.get_state()
env.reset()
img = cv2.imread('controller.jpg')
drawn = cv2.imread('controller.jpg')
while movie.step():
    keys = []
    for p in range(movie.players):
        for i in range(env.num_buttons):
            keys.append(movie.get_key(i, p))
    move = get_move(keys)
    env.step(keys)
    env.render()
    draw_image(img, drawn, move)
cv2.destroyAllWindows()