        program aggiungilambda

        open(10,file='numeropick.txt')
        read(10,*) cdp,npick

        open(14,file='residuo.txt')
        write(14,*) npick

        open(16,file='deltap.txt')

        open(12,file='mpicks.txt')
        do i=1,npick
         read(12,*) z,r
         read(16,*) delta
         write(14,*) cdp,z,r,delta
        enddo
        close(10)
        close(12)
        close(14)
        close(16)

        stop
        end
