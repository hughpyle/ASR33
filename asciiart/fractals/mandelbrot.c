/*
  mandel.c
  ascii print of mandelbrot fractals
  iterates Z _ Z^2 + C where C is in the region to explore
  target: 2.11BSD Unix
*/

#include <stdio.h>
#include <stdlib.h>

char chars[] = ".-_+><!=:*35CV49FO6D#AZUGS02$%P&WXEQH8B@KRNM";

/* dimensions of the printed plot (characters) */
#define X1 69
#define Y1 40

int main (argc,argv)
int argc;
char *argv[];
{
    char ch;
    int X, Y, N, M;
    double A, B, R1, R2, R3, I1, I2, I3, S1, S2, Z1, Z2;

    /* center coordinate of the plot, and dimensions */
    double R = -1.0;
    double I = 0.0;
    double D = 2.0;

    /* optional arguments: R I D */
    if(argc>1) {
        R = atof(argv[1]);
    }
    if(argc>2) {
        I = atof(argv[2]);
    }
    if(argc>3) {
        D = atof(argv[3]);
        if(D == 0.0) {
            D = 2.0;
        }
    }

    /* maximum number of iterations */
    M = 10 * (sizeof(chars)-1);

    /* boundary box on the complex plane */
    R1 = R - D;
    R2 = R + D;
    I1 = I - (D * 4/3 * Y1/X1);
    I2 = I + (D * 4/3 * Y1/X1);
    S1 = (R2 - R1) / X1;
    S2 = (I2 - I1) / Y1;

    /* iterate each row in the printed plot */
    for(Y=0; Y<=Y1; Y++) {
        I3 = I1 + S2 * Y;
        /* iterate each column */
        for(X=0; X<=X1; X++) {
            R3 = R1 + S1 * X;
            Z1 = R3;
            Z2 = I3;
            N = 1;
            while(1) {
                A = Z1 * Z1;
                B = Z2 * Z2;
                if(A+B > 4.0) {
                    /* enough already */
                    ch = chars[N % (sizeof(chars)-1)];
                    break;
                }
                if(N > M) {
                    /* failed to converge, fill as blank */
                    ch = ' ';
                    break;
                }
                Z2 = 2 * Z1 * Z2 + I3;
                Z1 = A - B + R3;
                N++;
            }
            printf("%c", ch);
        }
        printf("\n");
    }
    printf("\n");
    exit(0);
}