import random
import time
import sys
from multiprocessing import Pool

random.seed()


def genList(size):
    randomList = []

    # initialize random list with values between 0 and 100
    for i in range(size):
        randomList.append(random.randint(0, 10))

    return randomList


# return the sum of all elements in the list
# This is the same as "return sum(inList)" but in long form for readability and emphasis
def sumList(inList):
    finalSum = 0

    # iterate over all values in the list, and calculate the cummulative sum
    for value in inList:
        finalSum = finalSum + value
    return finalSum


def doWork(N):
    # create a random list of N integers
    myList = genList(N)
    finalSum = sumList(myList)
    return finalSum


if __name__ == '__main__':
        N = float(100000000)
        # mark the start time
        startTime = time.time()

        # create a process Pool with 4 processes
        pool = Pool(processes=4)

        # map doWork to availble Pool processes
        results = pool.map(doWork, (int(N / 4), int(N / 4), int(N / 4), int(N / 4)))

        # sum the partial results to get the final result
        finalSum = sumList(results)

        # mark the end time
        endTime = time.time()
        # calculate the total time it took to complete the work
        workTime = endTime - startTime

        # print results
        print("The job took " + str(workTime) + " seconds to complete")
        print("The final sum was: " + str(finalSum))