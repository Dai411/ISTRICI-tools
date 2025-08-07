        program sommavel

        open(10,file='velres.dat')
        open(12,file='vfile.a')
        open(16,file='vfile.updated')

        open(14,file='v.par')
        read(14,*) nz
        read(14,*) dz
        read(14,*) fz
        read(14,*) nx
        read(14,*) dx
        read(14,*) fx
        read(14,*) ncdpmin
        read(14,*) ncdpmax
        read(14,*) ncdp
        close(14)

        do i=1,nx
         do j=1,nz
          read(10,*) velres
          read(12,*) vel
          write(16,*) vel+velres
         enddo
        enddo
        close(10)
        close(12)
        close(16)

        stop
        end
