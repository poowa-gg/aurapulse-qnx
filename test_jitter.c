#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/neutrino.h>

int main(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    printf("===========================================\n");
    printf("  AuraPulse QNX 8.0 Kernel Boot Verified   \n");
    printf("  Timestamp: %ld sec, %ld nsec\n", ts.tv_sec, ts.tv_nsec);
    printf("===========================================\n");
    return 0;
}
