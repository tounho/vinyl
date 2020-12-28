#pragma once

class Stopwatch
{
private:
	size_t maximum;
	std::list<float> values;

	std::chrono::time_point<std::chrono::steady_clock> last;

public:
	Stopwatch(size_t maximum = 200);
	~Stopwatch();

	void Start();
	void Stop();
	void Lap();
	void Reset();

	float size();

	float movingAverage();
	float weightedMovingAverage();
};

