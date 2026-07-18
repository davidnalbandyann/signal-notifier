#pragma once

#include <cstddef>
#include <stdexcept>
#include <vector>

template <typename T>
class CircularBuffer {
public:
    explicit CircularBuffer(size_t capacity)
        : data_(capacity),
          capacity_(capacity),
          head_(0),
          count_(0) {}

    void push(const T& value) {
        if (count_ < capacity_) {
            data_[count_] = value;
            ++count_;
        } else {
            data_[head_] = value;
            head_ = (head_ + 1) % capacity_;
        }
    }

    size_t size() const { return count_; }
    size_t capacity() const { return capacity_; }
    bool full() const { return count_ == capacity_; }
    bool empty() const { return count_ == 0; }

    const T& at(size_t i) const {
        if (i >= count_) {
            throw std::out_of_range("CircularBuffer::at");
        }
        return data_[(head_ + i) % capacity_];
    }

    const T& operator[](size_t i) const { return at(i); }

    const T& latest() const {
        if (count_ == 0) {
            throw std::out_of_range("CircularBuffer::latest on empty buffer");
        }
        return data_[(head_ + count_ - 1) % capacity_];
    }

    const T& oldest() const {
        if (count_ == 0) {
            throw std::out_of_range("CircularBuffer::oldest on empty buffer");
        }
        return data_[head_];
    }

    T* begin() { return data_.data(); }
    const T* begin() const { return data_.data(); }
    T* end() { return data_.data() + count_; }
    const T* end() const { return data_.data() + count_; }

private:
    std::vector<T> data_;
    size_t capacity_;
    size_t head_;
    size_t count_;
};
