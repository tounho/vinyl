#include "pch.h"
#include "stopwatch.h"

/** For meassureing the time between cycles
 *  and calculating an average. Not imporant.
 */

Stopwatch::Stopwatch(size_t maximum) {
	this->maximum = maximum;
	values = std::list<float>();
}

Stopwatch::~Stopwatch() { }

void Stopwatch::Start() {
	if (last == std::chrono::time_point<std::chrono::steady_clock>()) last = std::chrono::high_resolution_clock::now();
}

void Stopwatch::Stop() {
	last = std::chrono::time_point<std::chrono::steady_clock>();
}

void Stopwatch::Lap() {
	if (last != std::chrono::time_point<std::chrono::steady_clock>()) {
		values.push_front(std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::high_resolution_clock::now() - last).count() / 1e9);
		if (values.size() > maximum) values.pop_back();
	}
	last = std::chrono::high_resolution_clock::now();
}

void Stopwatch::Reset() {
	Stop();
	values.clear();
}

float Stopwatch::size() {
	return values.size();
}

float Stopwatch::movingAverage() {
	if (values.size() == 0) return 0.0f;
	return (std::accumulate<std::list<float>::const_iterator, float>(values.begin(), values.end(), 0.0f) / values.size());
}

float Stopwatch::weightedMovingAverage() {
	if (values.size() == 0) return 0.0f;

	size_t n = values.size();
	size_t m = values.size();
	float wra = 0.0f;

	for (std::list<float>::const_iterator it = values.cbegin(); it != values.cend(); it++) {
		wra += n * *it;
		n--;
	}
	return wra / (.5f * m * (m + 1));;
}

