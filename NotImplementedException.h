#pragma once

class NotImplementedException : public std::logic_error
{
public:
	NotImplementedException();
	~NotImplementedException();
};