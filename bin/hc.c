#include <stdio.h>
#include <term.h>
/* compile with "gcc $(pkg-config --cflags --libs ncurses) hc.c -o hc" */
/* pls excuse the <%...%> alternative tokens, teletype 33 has no curly braces */
int main() <%
	int errret;
	setupterm((char *)0, /* fd */1, &errret);
	int hc = tigetflag("hc");
	switch(hc) <%
		case -1:
			puts("no information available");
			break;
		case 0:
			puts("not a hardcopy terminal");
			break;
		default:
			puts("this is a hardcopy terminal");
			break;
	%>
%>
