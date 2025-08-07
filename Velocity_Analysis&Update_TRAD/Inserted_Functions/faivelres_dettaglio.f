        program faivelres
        dimension res(100000,100,4),resint(100000,10000)

        open(10,file='residuotot.dat')
        open(12,file='v.par')
        read(12,*) nz
        read(12,*) ndz
        read(12,*) nfz
        read(12,*) nx
        read(12,*) ndx
        read(12,*) nfx
        read(12,*) ncdpmin
        read(12,*) ncdpmax
        read(12,*) ndcdp
        close(12)

 10     read(10,*,end=99) nc
        do i=1,nc
         read(10,*) cdp,z,r,xlam
         ncdp=int(cdp)
         ni=(ncdp-nfx)/ndx+1
         res(ni,i,1)=z
         res(ni,i,2)=r
         res(ni,i,3)=xlam
         res(ni,i,4)=nc 
        enddo
        goto 10
 99     close(10)
       
        nmin=(ncdpmin-nfx)/ndx+1
        nmax=(ncdpmax-nfx)/ndx+1
        nstep=ndcdp/ndx 

        do i=nmin,nmax,nstep
         do j=1,nz
          z=fz+ndz*(j-1)

c esclude un cig
         if(res(i,1,3).eq.999) then
          resint(i,j)=999
          goto 20
         endif
cccccccccccc

          do k=1,int(res(i,1,4))

           if(z.le.res(i,k,1).and.k.eq.1) then
            resint(i,j)=res(i,k,3)
            goto 20
           endif

           if(z.gt.res(i,k,1).and.k.ne.int(res(i,1,4)).and.
     $        z.le.res(i,k+1,1)) then
            xm=(res(i,k+1,3)-res(i,k,3))/(res(i,k+1,1)-res(i,k,1))
            xq=res(i,k,3)-xm*res(i,k,1)
            resint(i,j)=xm*z+xq
            goto 20
           endif

           if(k.eq.int(res(i,1,4))) then
            resint(i,j)=res(i,k,3)
            goto 20
           endif

          enddo
 20      enddo
        enddo

c fine interpolazione verticale
c check esclusione cig
c metto a posto l primo e l'ultimo
       if(resint(nmin,1).eq.999) then
        do k=nmin+nstep,nmax,nstep
         if(resint(k,1).ne.999) then
          do j=1,nz        
           resint(nmin,j)=resint(k,j)
          enddo
          goto 88
         endif           
        enddo
        endif

 88    if(resint(nmax,1).eq.999) then
        do k=nmax-nstep,nmin,-nstep       
         if(resint(k,1).ne.999) then
          do j=1,nz
           resint(nmax,j)=resint(k,j)
          enddo
          goto 77 
         endif
        enddo
        endif

c metto a posto gli altri 999 
 77     do i=nmin,nmax,nstep
          x=nfx+(i-1)*ndx!!!!!!!!!!!!
         if(resint(i,1).eq.999) then
          do k=i+nstep,nmax,nstep          
           if(resint(k,1).ne.999) then
            nvalido=k
            goto 66
           endif
          enddo

 66       do j=1,nz
           z=nfz+(j-1)*ndz
              xm=(resint(i-nstep,j)-resint(nvalido,j))/
     $     ((nvalido-i+nstep)*ndx)
              xq=resint(i-nstep,j)-xm*(nfx+(i-nstep)*ndx)
              resint(i,j)=xm*x+xq
          enddo
         endif
        enddo
ccccccccccccccccccc

        do j=1,nz
         z=nfz+(j-1)*ndz
         do i=1,nx
          x=nfx+(i-1)*ndx
         
          if(i.le.nmin) then
           resint(i,j)=0. !resint(nmin,j)
           goto 30
          endif

          if(i.ge.nmax) then
           resint(i,j)=0. !resint(nmax,j)
           goto 30
          endif

          nk=((i-nmin)/nstep)*nstep+nmin      

          xm=(resint(nk+nstep,j)-resint(nk,j))/(nstep*ndx)
          xq=resint(nk,j)-xm*(nfx+(nk-1)*ndx)
          resint(i,j)=xm*x+xq

 30      enddo
        enddo

c finita interpolazione dei cip analizzati

        open(50,file='velres.dat')
        do i=1,nx
         do j=1,nz
          write(50,*) resint(i,j)
         enddo
        enddo
        close(50)

        stop
        end
