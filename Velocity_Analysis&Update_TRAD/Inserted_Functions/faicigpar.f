        program faicigpar
        character cip*4,vir*1

        cip="cip="
        vir=","

        open(10,file='nciclo.txt')
        read(10,*) nc
        read(10,*) ncdp
        close(10)

        open(12,file='mpicks.txt')
        do i=1,nc
         read(12,*) z,t
        enddo
        close(12)

        open(14,file='cig.txt')
        write(14,'(a4,i10,a1,f10.4,a1,f10.8)') cip,ncdp,vir,z,vir,t
        close(14)
        
        stop
        end 
