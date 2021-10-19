import retro
import time

start_time = time.time()

def main():
    env = retro.make(game='Airstriker-Genesis')
    obs = env.reset()
    counter = 0
    episode_score = 0
    while counter < 1000:
        obs, rew, done, info = env.step(env.action_space.sample())
        env.render()
        episode_score += rew
        if done:
            obs = env.reset()
            print(f"fRun {counter} Finished. Score {episode_score}")
            episode_score = 0
            counter += 1


if __name__ == "__main__":
    start_time = time.time()
    main()
    print("--- %s seconds ---" % (time.time() - start_time))