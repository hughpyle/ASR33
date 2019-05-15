110 REM MANDELBROT SET - BWBASIC
120 REM ITERATES Z _ Z^2 + C WHERE C IS IN THE REGION TO EXPLORE
130 DIM C$(72)
140 C$=".-_+><!=:*35CV49FO6D#AZUGS02$%P&WXEQH8B@KRNM "
150 REM DIMENSIONS OF THE PRINTED PLOT (CHARACTERS)
160 X1=69
170 Y1=40
180 REM MAXIMUM NUMBER OF ITERATIONS
190 M = LEN(C$) * 10
200 REM CENTER COORDINATE OF THE PLOT, AND DIMENSIONS
210 R =-1
220 I = 0
230 D = 2
240 REM BOUNDARY BOX ON THE COMPLEX PLANE
250 R1 = R - D
260 R2 = R + D
270 I1 = I - (D * 4/3 * Y1/X1)
280 I2 = I + (D * 4/3 * Y1/X1)
290 S1=(R2-R1)/X1
300 S2=(I2-I1)/Y1
310 REM ITERATE EACH ROW IN THE PRINTED PLOT
320 FOR Y=0 TO Y1
330 I3=I1+S2*Y
340 REM ITERATE EACH COLUMN
350 FOR X=0 TO X1
360 R3=R1+S1*X
370 Z1=R3
380 Z2=I3
390 FOR N=1 TO M
400 A=Z1*Z1
410 B=Z2*Z2
420 IF A+B>4.0 THEN 480
430 Z2=2*Z1*Z2+I3
440 Z1=A-B+R3
450 NEXT N
460 REM THIS DIDN'T CONVERGE, SO FILL AS BLANK
470 N=LEN(C$)-1
480 E = N MOD LEN(C$) + 1
490 PRINT MID$(C$, E, 1);
500 NEXT X
510 PRINT
520 NEXT Y
530 END
