# Enter your code here. Read input from STDIN. Print output to STDOUT
t=input()
while(t>0):
    t-=1
    n,m=[int(i) for i in raw_input().split()]
    x_=list()
    y_=list()
    z_=list()
    w_=list()
    k=0
    cube=[[[0 for x in range(n+1)] for x in range(n+1)] for x in range(n+1)] 
    #print cube
    for j in range(0,m):
        inp=[i for i in raw_input().split()]
        if(inp[0]=="UPDATE"):
            x=int(inp[1])
            y=int(inp[2])
            z=int(inp[3])
            w=int(inp[4])
            x_.append(x)
            y_.append(y)
            z_.append(z)
            w_.append(w)
            k+=1
            cube[x][y][z]=w
        else:
            x1=int(inp[1])
            y1=int(inp[2])
            z1=int(inp[3])
            x2=int(inp[4])
            y2=int(inp[5])
            z2=int(inp[6])
            sum=0
            for p in range(0,k):
                if(x_[p]>=x1 and y_[p]>=y1 and z_[p]>=z1 and x_[p]<=x2 and y_[p]<=y2 and z_[p]<=z2):
                    sum+=w_[p]
            print sum
        
            







