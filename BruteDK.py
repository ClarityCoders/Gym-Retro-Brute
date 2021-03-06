"""
Implementation of the Brute from "Revisiting the Arcade Learning Environment:
Evaluation Protocols and Open Problems for General Agents" by Machado et al.
https://arxiv.org/abs/1709.06009

This is an agent that uses the determinism of the environment in order to do
pretty well at a number of retro games.  It does not save emulator state but
does rely on the same sequence of actions producing the same result when played
back.
"""

import random
import argparse

import numpy as np
import retro
import gym

class Discretizer(gym.ActionWrapper):
    """
    Wrap a gym environment and make it use discrete actions.

    Args:
        combos: ordered list of lists of valid button combinations
    """

    def __init__(self, env, combos):
        super().__init__(env)
        assert isinstance(env.action_space, gym.spaces.MultiBinary)
        buttons = env.unwrapped.buttons
        self._decode_discrete_action = []
        for combo in combos:
            arr = np.array([False] * env.action_space.n)
            for button in combo:
                arr[buttons.index(button)] = True
            self._decode_discrete_action.append(arr)

        self.action_space = gym.spaces.Discrete(len(self._decode_discrete_action))

    def action(self, act):
        return self._decode_discrete_action[act].copy()


# Change this depending on your game to map what buttons you want to allow.
class DonkeyKongDiscretizer(Discretizer):
    #Y Roll
    #B Jump
    #X Nothing
    #down Duck
    #A Switch Characters get off animal
    #Down Y ground slap
    def __init__(self, env):
        super().__init__(env=env, combos=[
            ['LEFT'],       #0 left
            ['RIGHT'],      #1 right 
            ['DOWN'],       #2 Down
            ['B'],          #3 Jump
            ['Y'],          #4 Roll
            ['A'],          #5 Switch character get off animal
            ['DOWN', 'Y'],
            ['LEFT', 'Y'],
            ['RIGHT', 'Y']   #6 Slap Ground
        ])

# This values changes how much the agent explores!
EXPLORATION_PARAM = 0.01

# This controls how often the agent makes a decision on a move.
# Default is 4
class Frameskip(gym.Wrapper):
    def __init__(self, env, skip=4):
        super().__init__(env)
        self._skip = skip

    def reset(self):
        return self.env.reset()

    def step(self, act):
        total_rew = 0.0
        done = None
        for i in range(self._skip):
            obs, rew, done, info = self.env.step(act)
            total_rew += rew
            if done:
                break

        return obs, total_rew, done, info

# Sets a time limit for the env
class TimeLimit(gym.Wrapper):
    def __init__(self, env, max_episode_steps=None):
        super().__init__(env)
        self._max_episode_steps = max_episode_steps
        self._elapsed_steps = 0

    def step(self, ac):
        observation, reward, done, info = self.env.step(ac)
        self._elapsed_steps += 1
        if self._elapsed_steps >= self._max_episode_steps:
            done = True
            info['TimeLimit.truncated'] = True
        return observation, reward, done, info

    def reset(self, **kwargs):
        self._elapsed_steps = 0
        return self.env.reset(**kwargs)


class Node:
    def __init__(self, value=-np.inf, children=None):
        self.value = value
        self.visits = 0
        self.children = {} if children is None else children

    def __repr__(self):
        return "<Node value=%f visits=%d len(children)=%d>" % (
            self.value,
            self.visits,
            len(self.children),
        )


def select_actions(root, action_space, max_episode_steps):
    """
    Select actions from the tree

    Normally we select the greedy action that has the highest reward
    associated with that subtree.  We have a small chance to select a
    random action based on the exploration param and visit count of the
    current node at each step.

    We select actions for the longest possible episode, but normally these
    will not all be used.  They will instead be truncated to the length
    of the actual episode and then used to update the tree.
    """
    node = root

    acts = []
    steps = 0
    while steps < max_episode_steps:
        if node is None:
            # we've fallen off the explored area of the tree, just select random actions
            act = action_space.sample()
        else:
            epsilon = EXPLORATION_PARAM / np.log(node.visits + 2)
            if random.random() < epsilon:
                # random action
                act = action_space.sample()
            else:
                # greedy action
                act_value = {}
                for act in range(action_space.n):
                    if node is not None and act in node.children:
                        act_value[act] = node.children[act].value
                    else:
                        act_value[act] = -np.inf
                best_value = max(act_value.values())
                best_acts = [
                    act for act, value in act_value.items() if value == best_value
                ]
                act = random.choice(best_acts)

            if act in node.children:
                node = node.children[act]
            else:
                node = None

        acts.append(act)
        steps += 1

    return acts


def rollout(env, acts):
    """
    Perform a rollout using a preset collection of actions
    """
    total_rew = 0
    env.reset()
    steps = 0
    for act in acts:
        _obs, rew, done, _info = env.step(act)
        steps += 1
        total_rew += rew
        if done:
            break

    return steps, total_rew


def update_tree(root, executed_acts, total_rew):
    """
    Given the tree, a list of actions that were executed before the game ended, and a reward, update the tree
    so that the path formed by the executed actions are all updated to the new reward.
    """
    root.value = max(total_rew, root.value)
    root.visits += 1
    new_nodes = 0

    node = root
    for step, act in enumerate(executed_acts):
        if act not in node.children:
            node.children[act] = Node()
            new_nodes += 1
        node = node.children[act]
        node.value = max(total_rew, node.value)
        node.visits += 1

    return new_nodes


class Brute:
    """
    Implementation of the Brute

    Creates and manages the tree storing game actions and rewards
    """

    def __init__(self, env, max_episode_steps):
        self.node_count = 1
        self._root = Node()
        self._env = env
        self._max_episode_steps = max_episode_steps

    def run(self):
        acts = select_actions(self._root, self._env.action_space, self._max_episode_steps)
        steps, total_rew = rollout(self._env, acts)
        executed_acts = acts[:steps]
        self.node_count += update_tree(self._root, executed_acts, total_rew)
        return executed_acts, total_rew


def brute_retro(
    game,
    max_episode_steps=6000,
    timestep_limit=1e8,
    state=retro.State.DEFAULT,
    scenario=None,
):
    env = retro.make(game=game, scenario=scenario)
    env = Frameskip(env)
    env = DonkeyKongDiscretizer(env)
    env = TimeLimit(env, max_episode_steps=max_episode_steps)

    brute = Brute(env, max_episode_steps=max_episode_steps)
    timesteps = 0
    best_rew = float('-inf')
    while True:
        acts, rew = brute.run()
        timesteps += len(acts)

        if rew > best_rew:
            print("new best reward {} => {}".format(best_rew, rew))
            print(brute._root)
            best_rew = rew
            env.unwrapped.record_movie(f"best-TimeStep-{timesteps}.bk2")
            env.reset()
            for act in acts:
                env.step(act)
            env.unwrapped.stop_record()

        if timesteps > timestep_limit:
            print("timestep limit exceeded")
            break

def main():

    # Change to game you want to play
    # You have to import ROM if it isn't one that's built into gym-retro
    # Airstriker-Genesis will work out of the box!
    game = 'Airstriker-Genesis'

    brute_retro(game=game, state=retro.State.DEFAULT, scenario=None)


if __name__ == "__main__":
    main()
