import sys

# Initialize denominator
k = 1
 
# Initialize sum
s = 0

#print ('Argument List:', str(sys.argv)) 
#print ('First argument:',  str(sys.argv[1]))

for i in range(int(sys.argv[1])):
 
    # even index elements are positive
    if i % 2 == 0:
        s += 4/k
    else:
 
        # odd index elements are negative
        s -= 4/k
 
    # denominator is odd
    k += 2
    #print(s)

print("After " +str(sys.argv[1])+ " loops, the value of pie is " + str(s))